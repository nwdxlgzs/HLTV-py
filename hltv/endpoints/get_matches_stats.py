from dataclasses import dataclass
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.game_map import from_map_slug, GameMap, to_map_filter
from ..shared.team import Team
from ..shared.event import Event
from ..shared.ranking_filter import RankingFilter
from ..shared.match_type import MatchType
from ..utils import fetch_page, get_id_at, sleep
from ..scraper import HLTVScraper

@dataclass
class GetMatchesStatsArguments:
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    matchType: Optional[MatchType] = None
    maps: Optional[List[GameMap]] = None
    rankingFilter: Optional[RankingFilter] = None
    delayBetweenPageRequests: int = 0

@dataclass
class MatchStatsPreview:
    mapStatsId: int
    date: int
    team1: Team
    team2: Team
    event: Event
    map: GameMap
    result: dict  # team1, team2

def get_matches_stats(config: HLTVConfig) -> Callable[[Optional[GetMatchesStatsArguments]], Awaitable[List[MatchStatsPreview]]]:
    async def inner(options: Optional[GetMatchesStatsArguments] = None) -> List[MatchStatsPreview]:
        options = options or GetMatchesStatsArguments()
        query = {}
        if options.startDate:
            query['startDate'] = options.startDate
        if options.endDate:
            query['endDate'] = options.endDate
        if options.matchType:
            query['matchType'] = options.matchType.value
        if options.maps:
            query['maps'] = [to_map_filter(m) for m in options.maps]
        if options.rankingFilter:
            query['rankingFilter'] = options.rankingFilter.value
        query_str = urlencode(query, doseq=True)

        page = 0
        all_matches: List[MatchStatsPreview] = []
        while True:
            await sleep(options.delayBetweenPageRequests)
            url = f'https://www.hltv.org/stats/matches?{query_str}&offset={page * 50}'
            soup = await fetch_page(url, config.load_page)
            hs = HLTVScraper(soup)
            rows = hs('.matches-table tbody tr').to_array()
            if not rows:
                break
            for el in rows:
                map_stats_id = el.find('.date-col a').attr_then('href', lambda h: get_id_at(4, h)) or 0
                date = el.find('.time').num_from_attr('data-unix') or 0
                map_slug = el.find('.dynamic-map-name-short').text()
                game_map = from_map_slug(map_slug)
                team1 = Team(
                    id=el.find('.team-col a').first().attr_then('href', lambda h: get_id_at(3, h)),
                    name=el.find('.team-col a').first().text()
                )
                team2 = Team(
                    id=el.find('.team-col a').last().attr_then('href', lambda h: get_id_at(3, h)),
                    name=el.find('.team-col a').last().text()
                )
                event_href = el.find('.event-col a').attr('href')
                event_id = int(event_href.split('event=')[1].split('&')[0]) if event_href else 0
                event_name = el.find('.event-col a').text()
                event = Event(id=event_id, name=event_name)
                score1_text = el.find('.team-col .score').first().trim_text().replace('(', '').replace(')', '')
                score2_text = el.find('.team-col .score').last().trim_text().replace('(', '').replace(')', '')
                try:
                    score1 = int(score1_text) if score1_text else 0
                    score2 = int(score2_text) if score2_text else 0
                except ValueError:
                    score1 = score2 = 0
                all_matches.append(MatchStatsPreview(
                    mapStatsId=map_stats_id,
                    date=date,
                    team1=team1,
                    team2=team2,
                    event=event,
                    map=game_map,
                    result={'team1': score1, 'team2': score2}
                ))
            page += 1
        return all_matches
    return inner