from dataclasses import dataclass, field
from typing import List, Optional, Callable, Awaitable, Dict, Any
from ..config import HLTVConfig
from ..shared.game_map import from_map_name, GameMap
from ..shared.team import Team
from ..shared.event import Event
from ..shared.player import Player
from ..utils import fetch_page, get_id_at, not_null, parse_number
from ..scraper import HLTVPage, HLTVElement, HLTVScraper

# ---------- 枚举 ----------
from enum import Enum


class Outcome(Enum):
    CTWin = 'ct_win'
    TWin = 't_win'
    BombDefused = 'bomb_defused'
    BombExploded = 'bomb_exploded'
    TimeRanOut = 'stopwatch'

# ---------- 数据结构 ----------


@dataclass
class PlayerStats:
    player: Player
    killsPerRound: Optional[float] = None
    deathsPerRound: Optional[float] = None
    impact: Optional[float] = None
    kills: int = 0
    hsKills: int = 0
    assists: int = 0
    flashAssists: int = 0
    deaths: int = 0
    KAST: Optional[float] = None
    killDeathsDifference: Optional[int] = None
    ADR: Optional[float] = None
    firstKillsDifference: Optional[int] = None
    rating1: Optional[float] = None
    rating2: Optional[float] = None


@dataclass
class TeamPerformance:
    kills: int = 0
    deaths: int = 0
    assists: int = 0


@dataclass
class TeamsPerformanceOverview:
    team1: TeamPerformance = field(default_factory=TeamPerformance)
    team2: TeamPerformance = field(default_factory=TeamPerformance)


@dataclass
class RoundOutcome:
    outcome: Outcome
    score: str
    tTeam: int
    ctTeam: int


@dataclass
class PlayerStat(Player):
    value: int = 0


@dataclass
class TeamStatComparison:
    team1: float = 0
    team2: float = 0


@dataclass
class MapStatsOverview:
    rating: TeamStatComparison = field(default_factory=TeamStatComparison)
    firstKills: TeamStatComparison = field(default_factory=TeamStatComparison)
    clutchesWon: TeamStatComparison = field(default_factory=TeamStatComparison)
    mostKills: Optional[PlayerStat] = None
    mostDamage: Optional[PlayerStat] = None
    mostAssists: Optional[PlayerStat] = None
    mostAWPKills: Optional[PlayerStat] = None
    mostFirstKills: Optional[PlayerStat] = None
    bestRating1: Optional[PlayerStat] = None
    bestRating2: Optional[PlayerStat] = None


@dataclass
class MapHalfResult:
    team1Rounds: int = 0
    team2Rounds: int = 0


@dataclass
class FullMatchMapStats:
    id: int
    matchId: int
    result: dict  # team1TotalRounds, team2TotalRounds, halfResults
    map: GameMap
    date: int
    team1: Team
    team2: Team
    event: Event
    overview: MapStatsOverview
    roundHistory: List[RoundOutcome]
    playerStats: dict  # {'team1': [...], 'team2': [...]}
    performanceOverview: TeamsPerformanceOverview

# ---------- 辅助函数 ----------


def get_overview_property_from_label(label: str) -> Optional[str]:
    mapping = {
        'Team rating': 'rating',
        'First kills': 'firstKills',
        'Clutches won': 'clutchesWon',
        'Most kills': 'mostKills',
        'Most damage': 'mostDamage',
        'Most assists': 'mostAssists',
        'Most AWP kills': 'mostAWPKills',
        'Most first kills': 'mostFirstKills',
        'Best rating 1.0': 'bestRating1',
        'Best rating 2.0': 'bestRating2',
    }
    return mapping.get(label)


def get_stats_overview(hs: 'HLTVPage') -> MapStatsOverview:
    overview = MapStatsOverview()
    # 队伍对比数据
    for row in hs('.match-info-row').to_array()[1:]:
        label = row.find('.bold').text()
        prop = get_overview_property_from_label(label)
        if not prop:
            continue
        parts = row.find('.right').text().split(' : ')
        if len(parts) == 2:
            try:
                setattr(overview, prop, TeamStatComparison(
                    team1=float(parts[0]), team2=float(parts[1])
                ))
            except ValueError:
                pass

    # Most-X 数据
    for box in hs('.most-x-box').to_array():
        label = box.find('.most-x-title').text()
        prop = get_overview_property_from_label(label)
        if not prop:
            continue
        player_href = box.find('.name > a').attr('href')
        player_id = get_id_at(3, player_href) if player_href else None
        player_name = box.find('.name > a').text()
        value = box.find('.valueName').num_from_text() or 0
        setattr(overview, prop, PlayerStat(
            name=player_name, id=player_id, value=value))
    return overview


def get_player_stats(m_hs: 'HLTVPage', p_hs: 'HLTVPage'):
    """解析两个页面的玩家统计数据，返回 {'team1': [...], 'team2': [...]}"""
    # 先解析性能页面图表中的数据
    perf_data: Dict[int, dict] = {}
    for el in p_hs('.highlighted-player').to_array():
        graph_data = el.find('.graph.small').attr(
            'data-fusionchart-config') or ''
        player_id_str = el.find('.headline span a').attr('href').split('/')[2]
        player_id = int(player_id_str)
        try:
            kills_per_round = float(graph_data.split(
                'Kills per round: ')[1].split('"')[0])
            deaths_per_round = float(graph_data.split(
                'Deaths / round: ')[1].split('"')[0])
            impact = float(graph_data.split(
                'Impact rating: ')[1].split('"')[0])
        except (IndexError, ValueError):
            kills_per_round = None
            deaths_per_round = None
            impact = None
        perf_data[player_id] = {
            'killsPerRound': kills_per_round,
            'deathsPerRound': deaths_per_round,
            'impact': impact
        }

    def parse_player_row(row: HLTVElement) -> PlayerStats:
        player_id = row.find(
            '.st-player a').attr_then('href', lambda h: get_id_at(3, h))
        if not player_id:
            return None
        name = row.find('.st-player a').text()
        player = Player(name=name, id=player_id)
        kills = row.find('.st-kills').contents().first().num_from_text() or 0
        hs_kills_text = row.find(
            '.st-kills .gtSmartphone-only').text().replace('(', '').replace(')', '')
        hs_kills = int(hs_kills_text) if hs_kills_text else 0
        assists = row.find(
            '.st-assists').contents().first().num_from_text() or 0
        flash_assists_text = row.find(
            '.st-assists .gtSmartphone-only').text().replace('(', '').replace(')', '')
        flash_assists = int(flash_assists_text) if flash_assists_text else 0
        deaths = row.find('.st-deaths').num_from_text() or 0
        kast_str = row.find('.st-kdratio').text()
        kast = parse_number(kast_str.replace('%', '')) if kast_str else None
        kd_diff = row.find('.st-kddiff').num_from_text()
        adr = row.find('.st-adr').num_from_text()
        fk_diff = row.find('.st-fkdiff').num_from_text()
        rating_val = row.find('.st-rating').num_from_text()
        rating1 = rating2 = None
        rating_desc = row.find('.st-rating .ratingDesc').text()
        if rating_desc == '2.0':
            rating2 = rating_val
        else:
            rating1 = rating_val

        pdata = perf_data.get(player_id, {})
        return PlayerStats(
            player=player,
            kills=kills,
            hsKills=hs_kills,
            assists=assists,
            flashAssists=flash_assists,
            deaths=deaths,
            KAST=kast,
            killDeathsDifference=kd_diff,
            ADR=adr,
            firstKillsDifference=fk_diff,
            rating1=rating1,
            rating2=rating2,
            killsPerRound=pdata.get('killsPerRound'),
            deathsPerRound=pdata.get('deathsPerRound'),
            impact=pdata.get('impact')
        )

    team1_stats = [parse_player_row(r) for r in m_hs(
        '.stats-table.totalstats').first().find('tbody tr').to_array()]
    team2_stats = [parse_player_row(r) for r in m_hs(
        '.stats-table.totalstats').last().find('tbody tr').to_array()]
    return {'team1': [s for s in team1_stats if s], 'team2': [s for s in team2_stats if s]}


def get_performance_overview(p_hs: 'HLTVPage') -> TeamsPerformanceOverview:
    perf = TeamsPerformanceOverview()
    for row in p_hs('.overview-table tr').to_array()[1:]:
        prop = row.find('.name-column').text().lower()
        team1_val = row.find('.team1-column').num_from_text() or 0
        team2_val = row.find('.team2-column').num_from_text() or 0
        if prop in ('kills', 'deaths', 'assists'):
            setattr(perf.team1, prop, team1_val)
            setattr(perf.team2, prop, team2_val)
    return perf

# ---------- 主端点 ----------


def get_match_map_stats(config: HLTVConfig) -> Callable[[dict], Awaitable[FullMatchMapStats]]:
    async def inner(params: dict) -> FullMatchMapStats:
        mid = params['id']
        url1 = f'https://www.hltv.org/stats/matches/mapstatsid/{mid}/-'
        url2 = f'https://www.hltv.org/stats/matches/performance/mapstatsid/{mid}/-'
        import asyncio
        m_soup, p_soup = await asyncio.gather(
            fetch_page(url1, config.load_page),
            fetch_page(url2, config.load_page)
        )
        m_hs = HLTVScraper(m_soup)
        p_hs = HLTVScraper(p_soup)

        match_id = m_hs('.match-page-link').attr_then('href',
                                                      lambda h: get_id_at(2, h)) or 0

        # 比分结果
        halfs_str = m_hs('.match-info-row .right').eq(0).text()
        import re
        half_matches = re.findall(r'(?<!\() \d+ : \d+ (?=\))', halfs_str)
        half_results = []
        for hm in half_matches:
            scores = hm.strip().split(' : ')
            half_results.append(MapHalfResult(
                team1Rounds=int(scores[0]),
                team2Rounds=int(scores[1])
            ))
        # 如果没有解析到，填充两个空
        if len(half_results) < 2:
            half_results += [MapHalfResult()
                             for _ in range(2 - len(half_results))]

        t1_rounds = m_hs('.team-left .bold').num_from_text() or 0
        t2_rounds = m_hs('.team-right .bold').num_from_text() or 0
        result = {
            'team1TotalRounds': t1_rounds,
            'team2TotalRounds': t2_rounds,
            'halfResults': half_results
        }

        map_name = m_hs('.match-info-box').contents().eq(3).trim_text()
        game_map = from_map_name(map_name)
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
        # 事件
        event_href = m_hs(
            '.match-info-box .text-ellipsis').first().attr('href')
        event_id = int(event_href.split('event=')[-1]) if event_href else 0
        event_name = m_hs('.match-info-box .text-ellipsis').first().text()
        event = Event(id=event_id, name=event_name)

        # 回合历史
        round_history = _get_round_history(m_hs, team1, team2)

        overview = get_stats_overview(m_hs)
        player_stats = get_player_stats(m_hs, p_hs)
        perf_overview = get_performance_overview(p_hs)

        return FullMatchMapStats(
            id=mid,
            matchId=match_id,
            result=result,
            map=game_map,
            date=date,
            team1=team1,
            team2=team2,
            event=event,
            overview=overview,
            roundHistory=round_history,
            playerStats=player_stats,
            performanceOverview=perf_overview
        )
    return inner


def _get_round_history(hs: 'HLTVPage', team1: Team, team2: Team) -> List[RoundOutcome]:
    def get_outcome(el: HLTVElement):
        src = el.attr('src') or ''
        outcome_str = src.split('/')[-1].split('.')[0]
        score = el.attr('title') or ''
        return outcome_str, score

    team1_outs = [get_outcome(el) for el in hs(
        '.round-history-team-row').first().find('.round-history-outcome').to_array()]
    team2_outs = [get_outcome(el) for el in hs(
        '.round-history-team-row').last().find('.round-history-outcome').to_array()]
    if not team1_outs:
        return []

    does_team1_start_ct = 'ct' in team1_outs[0][0].lower()
    separator_index = hs(
        '.round-history-team-row .round-history-bar').last().index() - 2

    history = []
    for i, (out1, out2) in enumerate(zip(team1_outs, team2_outs)):
        if out1[0] == 'emptyHistory' and out2[0] == 'emptyHistory':
            continue
        if out1[0] == 'emptyHistory':
            outcome_raw = out2[0]
            score = out2[1]
        else:
            outcome_raw = out1[0]
            score = out1[1]
        outcome = Outcome(
            outcome_raw) if outcome_raw in Outcome._value2member_map_ else Outcome.CTWin

        if i < separator_index:
            if does_team1_start_ct:
                t_team = team2.id
                ct_team = team1.id
            else:
                t_team = team1.id
                ct_team = team2.id
        else:
            if does_team1_start_ct:
                t_team = team1.id
                ct_team = team2.id
            else:
                t_team = team2.id
                ct_team = team1.id
        history.append(RoundOutcome(outcome=outcome,
                       score=score, tTeam=t_team, ctTeam=ct_team))
    return history
