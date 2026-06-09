from dataclasses import dataclass, field
from typing import List, Optional, Callable, Awaitable
from ..config import HLTVConfig
from ..shared.team import Team
from ..shared.event import Event
from ..utils import fetch_page, get_id_at
from ..scraper import HLTVScraper
from .get_match_map_stats import (
    MapStatsOverview,
    TeamsPerformanceOverview,
    PlayerStats,
    get_stats_overview,
    get_player_stats,
    get_performance_overview
)


@dataclass
class FullMatchStats:
    id: int
    matchId: int
    mapStatIds: List[int]
    result: dict  # team1MapsWon, team2MapsWon
    date: int
    team1: Team
    team2: Team
    event: Event
    overview: MapStatsOverview
    playerStats: dict
    performanceOverview: TeamsPerformanceOverview


def get_match_stats(config: HLTVConfig) -> Callable[[dict], Awaitable[FullMatchStats]]:
    async def inner(params: dict) -> FullMatchStats:
        match_id = params['id']
        import asyncio
        m_soup, p_soup = await asyncio.gather(
            fetch_page(
                f'https://www.hltv.org/stats/matches/{match_id}/-', config.load_page),
            fetch_page(
                f'https://www.hltv.org/stats/matches/performance/{match_id}/-', config.load_page)
        )
        m_hs = HLTVScraper(m_soup)
        p_hs = HLTVScraper(p_soup)

        linked_match_id = m_hs(
            '.match-page-link').attr_then('href', lambda h: get_id_at(2, h)) or 0
        map_stat_ids = [
            el.attr_then('href', lambda h: get_id_at(4, h))
            for el in m_hs('.stats-match-map.inactive').to_array()
        ]
        map_stat_ids = [x for x in map_stat_ids if x is not None]

        result = {
            'team1MapsWon': m_hs('.team-left .bold').num_from_text() or 0,
            'team2MapsWon': m_hs('.team-right .bold').num_from_text() or 0
        }
        date = m_hs(
            '.match-info-box span[data-time-format]').num_from_attr('data-unix') or 0
        team1 = Team(
            id=m_hs('.team-left a').attr_then('href',
                                              lambda h: get_id_at(3, h)),
            name=m_hs('.team-left .team-logo').attr('title')
        )
        team2 = Team(
            id=m_hs('.team-right a').attr_then('href',
                                               lambda h: get_id_at(3, h)),
            name=m_hs('.team-right .team-logo').attr('title')
        )
        event_href = m_hs(
            '.match-info-box .text-ellipsis').first().attr('href')
        event_id = int(event_href.split('event=')[-1]) if event_href else 0
        event_name = m_hs('.match-info-box .text-ellipsis').first().text()
        event = Event(id=event_id, name=event_name)

        overview = get_stats_overview(m_hs)
        player_stats = get_player_stats(m_hs, p_hs)
        perf_overview = get_performance_overview(p_hs)

        return FullMatchStats(
            id=match_id,
            matchId=linked_match_id,
            mapStatIds=map_stat_ids,
            result=result,
            date=date,
            team1=team1,
            team2=team2,
            event=event,
            overview=overview,
            playerStats=player_stats,
            performanceOverview=perf_overview
        )
    return inner
