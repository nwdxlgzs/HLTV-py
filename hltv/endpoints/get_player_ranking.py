from dataclasses import dataclass
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.best_of_filter import BestOfFilter
from ..shared.game_map import GameMap, to_map_filter
from ..shared.match_type import MatchType
from ..shared.player import Player
from ..shared.ranking_filter import RankingFilter
from ..shared.team import Team
from ..utils import fetch_page, get_id_at
from ..scraper import HLTVScraper


@dataclass
class PlayerRanking:
    player: Player
    teams: List[Team]
    maps: int
    kdDiff: int
    rounds: int
    kd: float
    rating1: Optional[float] = None
    rating2: Optional[float] = None


@dataclass
class GetPlayerRankingOptions:
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    matchType: Optional[MatchType] = None
    rankingFilter: Optional[RankingFilter] = None
    maps: Optional[List[GameMap]] = None
    minMapCount: Optional[int] = None
    countries: Optional[List[str]] = None
    bestOfX: Optional[BestOfFilter] = None


def get_player_ranking(config: HLTVConfig) -> Callable[[Optional[GetPlayerRankingOptions]], Awaitable[List[PlayerRanking]]]:
    async def inner(options: Optional[GetPlayerRankingOptions] = None) -> List[PlayerRanking]:
        options = options or GetPlayerRankingOptions()
        query = {}
        if options.startDate:
            query['startDate'] = options.startDate
        if options.endDate:
            query['endDate'] = options.endDate
        if options.matchType:
            query['matchType'] = options.matchType.value
        if options.rankingFilter:
            query['rankingFilter'] = options.rankingFilter.value
        if options.maps:
            query['maps'] = [to_map_filter(m) for m in options.maps]
        if options.minMapCount:
            query['minMapCount'] = options.minMapCount
        if options.countries:
            query['country'] = options.countries
        if options.bestOfX:
            query['bestOfX'] = options.bestOfX.value
        query_str = urlencode(query, doseq=True)
        url = f'https://www.hltv.org/stats/players?{query_str}'
        soup = await fetch_page(url, config.load_page)
        hs = HLTVScraper(soup)

        rating_desc = hs('.ratingCol .ratingDesc').text()
        is_rating2 = rating_desc == '2.0'

        rankings = []
        for el in hs('.player-ratings-table tbody tr').to_array():
            player_id = el.find('.playerCol a').attr_then(
                'href', lambda h: get_id_at(3, h))
            player_name = el.find('.playerCol a').text()
            player = Player(name=player_name, id=player_id)

            teams = []
            for team_el in el.find('.teamCol a').to_array():
                teams.append(Team(
                    id=team_el.attr_then('href', lambda h: get_id_at(3, h)),
                    name=team_el.find('img').attr('title')
                ))
            maps = el.find('td.statsDetail').eq(0).num_from_text() or 0
            rounds = el.find('td.statsDetail').eq(1).num_from_text() or 0
            kd_diff = el.find('td.kdDiffCol').num_from_text() or 0
            kd = el.find('td.statsDetail').eq(2).num_from_text() or 0.0
            rating = el.find('td.ratingCol').num_from_text() or 0.0

            if is_rating2:
                rankings.append(PlayerRanking(
                    player=player, teams=teams, maps=maps,
                    kdDiff=kd_diff, rounds=rounds, kd=kd, rating2=rating
                ))
            else:
                rankings.append(PlayerRanking(
                    player=player, teams=teams, maps=maps,
                    kdDiff=kd_diff, rounds=rounds, kd=kd, rating1=rating
                ))
        return rankings
    return inner
