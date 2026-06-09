from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.best_of_filter import BestOfFilter
from ..shared.game_map import from_map_name, GameMap, to_map_filter
from ..shared.match_type import MatchType
from ..shared.player import Player
from ..shared.event import Event
from ..shared.ranking_filter import RankingFilter
from ..shared.team import Team
from ..utils import fetch_page, generate_random_suffix, get_id_at
from ..scraper import HLTVPage, HLTVElement, HLTVScraper
from .get_matches_stats import MatchStatsPreview


@dataclass
class TeamMapStats:
    wins: int = 0
    draws: int = 0
    losses: int = 0
    winRate: float = 0.0
    totalRounds: int = 0
    roundWinPAfterFirstKill: float = 0.0
    roundWinPAfterFirstDeath: float = 0.0


@dataclass
class TeamStatsEvent:
    place: str
    event: Event


@dataclass
class FullTeamStats:
    id: int
    name: str
    overview: dict  # mapsPlayed, wins, draws, losses, totalKills, totalDeaths, roundsPlayed, kdRatio
    currentLineup: List[Player]
    historicPlayers: List[Player]
    standins: List[Player]
    substitutes: List[Player]
    matches: List[MatchStatsPreview]
    mapStats: Dict[str, TeamMapStats]  # key is GameMap.value
    events: List[TeamStatsEvent]


@dataclass
class GetTeamStatsArguments:
    id: int
    currentRosterOnly: bool = False
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    matchType: Optional[MatchType] = None
    rankingFilter: Optional[RankingFilter] = None
    maps: Optional[List[GameMap]] = None
    bestOfX: Optional[BestOfFilter] = None


def get_team_stats(config: HLTVConfig) -> Callable[[GetTeamStatsArguments], Awaitable[FullTeamStats]]:
    async def inner(options: GetTeamStatsArguments) -> FullTeamStats:
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
        if options.bestOfX:
            query['bestOfX'] = options.bestOfX.value
        query_str = urlencode(query, doseq=True)
        team_id = options.id

        # 初始页面（球队总览）
        initial_url = f'https://www.hltv.org/stats/teams/{team_id}/-?{query_str}'
        soup = await fetch_page(initial_url, config.load_page)
        hs = HLTVScraper(soup)

        name = hs('.context-item-name').last().text()

        def get_players_by_container(container: HLTVElement) -> List[Player]:
            players = []
            for el in container.find('.image-and-label').to_array():
                players.append(Player(
                    id=el.attr_then('href', lambda h: get_id_at(3, h)),
                    name=el.find('.text-ellipsis').text()
                ))
            return players

        def get_container_by_text(text: str) -> HLTVElement:
            for el in hs('.standard-headline').to_array():
                if el.text() == text:
                    return el.parent().next()
            return hs('')

        current_lineup = get_players_by_container(
            get_container_by_text('Current lineup'))
        historic_players = get_players_by_container(
            get_container_by_text('Historic players'))
        standins = get_players_by_container(get_container_by_text('Standins'))
        substitutes = get_players_by_container(
            get_container_by_text('Substitutes'))

        # 如果只查看当前阵容，重新抓取 lineup 页面作为基础
        if options.currentRosterOnly:
            lineup_query = urlencode({
                'lineup': [p.id for p in current_lineup if p.id is not None],
                'minLineupMatch': 0
            }, doseq=True)
            lineup_url = f'https://www.hltv.org/stats/lineup?{lineup_query}'
            soup = await fetch_page(lineup_url, config.load_page)
            hs = HLTVScraper(soup)
            # 用 lineup 统计更新 overview，下面会重新读取 overview 数据

        # 三页面并行抓取：比赛、赛事、地图统计
        import asyncio
        base_params = f'?{query_str}' if query_str else ''
        if options.currentRosterOnly:
            # 对于 lineup 模式，三个页面 URL 不同
            # 需要用到 currentLineup ids 构建 lineup query
            lineup_query_full = urlencode({
                'lineup': [p.id for p in current_lineup if p.id is not None],
                'minLineupMatch': 0
            }, doseq=True)
            matches_url = f'https://www.hltv.org/stats/lineup/matches?{lineup_query_full}&{query_str}'
            events_url = f'https://www.hltv.org/stats/lineup/events?{lineup_query_full}&{query_str}'
            maps_url = f'https://www.hltv.org/stats/lineup/maps?{lineup_query_full}&{query_str}'
        else:
            rand = generate_random_suffix()
            matches_url = f'https://www.hltv.org/stats/teams/matches/{team_id}/{rand}{base_params}'
            events_url = f'https://www.hltv.org/stats/teams/events/{team_id}/{rand}{base_params}'
            maps_url = f'https://www.hltv.org/stats/teams/maps/{team_id}/{rand}{base_params}'

        m_soup, e_soup, mp_soup = await asyncio.gather(
            fetch_page(matches_url, config.load_page),
            fetch_page(events_url, config.load_page),
            fetch_page(maps_url, config.load_page)
        )
        m_hs = HLTVScraper(m_soup)
        e_hs = HLTVScraper(e_soup)
        mp_hs = HLTVScraper(mp_soup)

        # 概览统计
        overview_stats = hs('.standard-box .large-strong')
        maps_played = overview_stats.eq(0).num_from_text() or 0
        wins_draws_losses = overview_stats.eq(1).text().split('/')
        wins = int(wins_draws_losses[0]) if len(wins_draws_losses) > 0 else 0
        draws = int(wins_draws_losses[1]) if len(wins_draws_losses) > 1 else 0
        losses = int(wins_draws_losses[2]) if len(wins_draws_losses) > 2 else 0
        total_kills = overview_stats.eq(2).num_from_text() or 0
        total_deaths = overview_stats.eq(3).num_from_text() or 0
        rounds_played = overview_stats.eq(4).num_from_text() or 0
        kd_ratio = overview_stats.eq(5).num_from_text() or 0

        overview = {
            'mapsPlayed': maps_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'totalKills': total_kills,
            'totalDeaths': total_deaths,
            'roundsPlayed': rounds_played,
            'kdRatio': kd_ratio
        }

        # 比赛列表
        current_team = Team(id=team_id, name=name)
        matches = []
        for el in m_hs('.stats-table tbody tr').to_array():
            # 比分解析
            result_text = el.find('.statsDetail').text()
            parts = result_text.split(' - ')
            score1 = int(parts[0]) if parts else 0
            score2 = int(parts[1]) if len(parts) > 1 else 0
            # 日期
            time_link = el.find('.time a')
            date_ts = _get_timestamp(time_link.text())
            # 对手信息
            opponent_el = el.find('img.flag').parent()
            opponent_id = opponent_el.attr_then(
                'href', lambda h: get_id_at(3, h))
            opponent_name = opponent_el.trim_text() or ''
            # 赛事
            event_el = el.find('.image-and-label').first()
            event_href = event_el.attr('href') or ''
            event_id = int(event_href.split('event=')[1].split('&')[
                           0]) if 'event=' in event_href else 0
            event_name = event_el.find('img').attr('title') or event_el.text()
            # 地图
            map_name = el.find('.statsMapPlayed').text()
            # mapStatsId
            map_stats_id = el.find('.time a').attr_then(
                'href', lambda h: get_id_at(4, h)) or 0
            matches.append(MatchStatsPreview(
                mapStatsId=map_stats_id,
                date=date_ts,
                team1=current_team,
                team2=Team(id=opponent_id, name=opponent_name),
                event=Event(id=event_id, name=event_name),
                map=from_map_name(map_name),
                result={'team1': score1, 'team2': score2}
            ))

        # 赛事成就
        events = []
        for el in e_hs('.stats-table tbody tr').to_array():
            event_el = el.find('.image-and-label').first()
            event_href = event_el.attr('href') or ''
            event_id = int(event_href.split('event=')[1].split('&')[
                           0]) if 'event=' in event_href else 0
            event_name = event_el.text()
            place = el.find('.statsCenterText').text()
            events.append(TeamStatsEvent(
                place=place, event=Event(id=event_id, name=event_name)))

        # 地图统计
        map_stats: Dict[str, TeamMapStats] = {}
        for col in mp_hs('.two-grid .col .stats-rows').to_array():
            # 找到地图名称（在前一个兄弟元素中）
            map_name_el = col.prev().find('.map-pool-map-name')
            if not map_name_el.exists():
                continue
            map_name = from_map_name(map_name_el.text())
            def get_map_stat(i): return col.find(
                '.stats-row').eq(i).children().last().text()

            wdl = get_map_stat(0).split(' / ')
            wins_m = int(wdl[0]) if len(wdl) > 0 else 0
            draws_m = int(wdl[1]) if len(wdl) > 1 else 0
            losses_m = int(wdl[2]) if len(wdl) > 2 else 0
            win_rate = float(get_map_stat(1).replace('%', ''))
            total_rounds = int(get_map_stat(2))
            win_after_first_kill = float(get_map_stat(3).replace('%', ''))
            win_after_first_death = float(get_map_stat(4).replace('%', ''))

            map_stats[map_name.value] = TeamMapStats(
                wins=wins_m, draws=draws_m, losses=losses_m,
                winRate=win_rate, totalRounds=total_rounds,
                roundWinPAfterFirstKill=win_after_first_kill,
                roundWinPAfterFirstDeath=win_after_first_death
            )

        return FullTeamStats(
            id=team_id,
            name=name,
            overview=overview,
            currentLineup=current_lineup,
            historicPlayers=historic_players,
            standins=standins,
            substitutes=substitutes,
            matches=matches,
            mapStats=map_stats,
            events=events
        )
    return inner


def _get_timestamp(source: str) -> int:
    """解析日期格式 dd/mm/yy 返回毫秒时间戳"""
    from datetime import datetime
    try:
        return int(datetime.strptime(source, '%d/%m/%y').timestamp() * 1000)
    except:
        return 0
