from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.best_of_filter import BestOfFilter
from ..shared.game_map import from_map_slug, GameMap, to_map_filter
from ..utils import fetch_page, get_id_at, sleep
from ..scraper import HLTVScraper


class ResultsMatchType(Enum):
    LAN = 'Lan'
    Online = 'Online'


class ContentFilter(Enum):
    HasHighlights = 'highlights'
    HasDemo = 'demo'
    HadVOD = 'vod'
    HasStats = 'stats'


class GameType(Enum):
    CSGO = 'CSGO'
    CS16 = 'CS16'


@dataclass
class ResultTeam:
    name: str
    logo: str


@dataclass
class FullMatchResult:
    id: int
    date: int
    team1: ResultTeam
    team2: ResultTeam
    stars: int
    format: str
    map: Optional[GameMap] = None
    result: dict = field(default_factory=dict)  # 现在 field 已正确导入


@dataclass
class GetResultsArguments:
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    matchType: Optional[ResultsMatchType] = None
    maps: Optional[List[GameMap]] = None
    bestOfX: Optional[BestOfFilter] = None
    countries: Optional[List[str]] = None
    contentFilters: Optional[List[ContentFilter]] = None
    eventIds: Optional[List[int]] = None
    playerIds: Optional[List[int]] = None
    teamIds: Optional[List[int]] = None
    game: Optional[GameType] = None
    stars: Optional[int] = None  # 1-5
    delayBetweenPageRequests: int = 0


def get_results(config: HLTVConfig) -> Callable[[GetResultsArguments], Awaitable[List[FullMatchResult]]]:
    async def inner(options: GetResultsArguments) -> List[FullMatchResult]:
        query = {}
        if options.startDate:
            query['startDate'] = options.startDate
        if options.endDate:
            query['endDate'] = options.endDate
        if options.matchType:
            query['matchType'] = options.matchType.value
        if options.maps:
            query['map'] = [to_map_filter(m) for m in options.maps]
        if options.bestOfX:
            query['bestOfX'] = options.bestOfX.value
        if options.countries:
            query['country'] = options.countries
        if options.contentFilters:
            query['content'] = [f.value for f in options.contentFilters]
        if options.eventIds:
            query['event'] = options.eventIds
        if options.playerIds:
            query['player'] = options.playerIds
        if options.teamIds:
            query['team'] = options.teamIds
        if options.game:
            query['gameType'] = options.game.value
        if options.stars:
            query['stars'] = options.stars
        query_str = urlencode(query, doseq=True)

        page = 0
        all_results: List[FullMatchResult] = []
        featured_ids = set()

        while True:
            await sleep(options.delayBetweenPageRequests)
            url = f'https://www.hltv.org/results?{query_str}&offset={page * 100}'
            soup = await fetch_page(url, config.load_page)
            hs = HLTVScraper(soup)

            # 特色比赛ID（只出现在第一页，可能被过滤）
            if page == 0:
                for el in hs('.big-results .result-con').to_array():
                    id_val = el.children().first().attr_then('href', lambda h: get_id_at(2, h))
                    if id_val:
                        featured_ids.add(id_val)

            rows = hs('.result-con').to_array()
            if not rows:
                break

            for el in rows:
                match_id = el.children().first().attr_then('href', lambda h: get_id_at(2, h))
                if not match_id:
                    continue
                if match_id in featured_ids:
                    continue

                stars = el.find('.stars i').length
                date = el.num_from_attr('data-zonedgrouping-entry-unix') or 0
                format_str = el.find('.map-text').text()
                team1_name = el.find('div.team').first().text()
                team1_logo = el.find('img.team-logo').first().attr('src') or ''
                team2_name = el.find('div.team').last().text()
                team2_logo = el.find('img.team-logo').last().attr('src') or ''
                score_str = el.find('.result-score').text()
                parts = score_str.split(' - ')
                score1 = int(parts[0]) if parts else 0
                score2 = int(parts[1]) if len(parts) > 1 else 0

                # 判断是 BOX 还是单图
                if 'bo' in format_str.lower():
                    map_info = None
                    fmt = format_str
                else:
                    map_info = from_map_slug(format_str)
                    fmt = 'bo1'

                all_results.append(FullMatchResult(
                    id=match_id,
                    stars=stars,
                    date=date,
                    team1=ResultTeam(name=team1_name, logo=team1_logo),
                    team2=ResultTeam(name=team2_name, logo=team2_logo),
                    result={'team1': score1, 'team2': score2},
                    map=map_info,
                    format=fmt
                ))
            page += 1

        return all_results
    return inner
