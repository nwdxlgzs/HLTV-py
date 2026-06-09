from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable, Awaitable
from ..config import HLTVConfig
from ..utils import fetch_page, generate_random_suffix, get_id_at, parse_number, percentage_to_decimal_odd
from ..scraper import HLTVScraper
from ..shared.game_map import from_map_name, GameMap
from ..shared.match_format import from_full_match_format, MatchFormat, MatchFormatLocation
from ..shared.player import Player
from ..shared.team import Team
from ..shared.event import Event

# ---------- 枚举 ----------


class MatchStatus(Enum):
    Live = 'Live'
    Postponed = 'Postponed'
    Over = 'Over'
    Scheduled = 'Scheduled'
    Deleted = 'Deleted'


class WinType(Enum):
    Lost = 'lost'
    TerroristsWin = 'Terrorists_Win'
    CTsWin = 'CTs_Win'
    TargetBombed = 'Target_Bombed'
    BombDefused = 'Bomb_Defused'

# ---------- 子数据结构 ----------


@dataclass
class Demo:
    name: str
    link: str


@dataclass
class Highlight:
    link: str
    title: str


@dataclass
class Veto:
    team: Optional[Team] = None
    map: Optional[GameMap] = None
    type: Optional[str] = None  # 'removed', 'picked', 'leftover'


@dataclass
class HeadToHeadResult:
    date: Optional[int] = None
    winner: Optional[Team] = None
    event: Optional[Event] = None
    map: Optional[GameMap] = None
    result: str = ''


@dataclass
class ProviderOdds:
    provider: str = ''
    team1: float = 0.0
    team2: float = 0.0


@dataclass
class MapHalfResult:
    team1Rounds: int = 0
    team2Rounds: int = 0


@dataclass
class MapResult:
    name: GameMap = GameMap.Default
    result: Optional['MapResultData'] = None
    statsId: Optional[int] = None


@dataclass
class MapResultData:
    team1TotalRounds: int = 0
    team2TotalRounds: int = 0
    halfResults: List[MapHalfResult] = field(default_factory=list)


@dataclass
class Stream:
    name: str = ''
    link: str = ''
    viewers: int = -1


@dataclass
class FullMatchTeam(Team):
    rank: Optional[int] = None


@dataclass
class FullMatch:
    id: int = 0
    statsId: Optional[int] = None
    title: Optional[str] = None
    date: Optional[int] = None
    significance: Optional[str] = None
    format: Optional[dict] = None
    status: MatchStatus = MatchStatus.Scheduled
    hasScorebot: bool = False
    team1: Optional[FullMatchTeam] = None
    team2: Optional[FullMatchTeam] = None
    winnerTeam: Optional[FullMatchTeam] = None
    vetoes: List[Veto] = field(default_factory=list)
    event: Optional[Event] = None
    odds: List[ProviderOdds] = field(default_factory=list)
    maps: List[MapResult] = field(default_factory=list)
    players: dict = field(default_factory=lambda: {'team1': [], 'team2': []})
    streams: List[Stream] = field(default_factory=list)
    demos: List[Demo] = field(default_factory=list)
    highlightedPlayers: Optional[dict] = None
    headToHead: List[HeadToHeadResult] = field(default_factory=list)
    highlights: List[Highlight] = field(default_factory=list)
    playerOfTheMatch: Optional[Player] = None

# ---------- 端点主函数 ----------


def get_match(config: HLTVConfig) -> Callable[[dict], Awaitable[FullMatch]]:
    async def inner(params: dict) -> FullMatch:
        match_id = params['id']
        soup = await fetch_page(
            f'https://www.hltv.org/matches/{match_id}/{generate_random_suffix()}',
            config.load_page
        )
        hs = HLTVScraper(soup)

        title = hs('.timeAndEvent .text').trim_text()
        date = hs('.timeAndEvent .date').num_from_attr('data-unix')
        format_info = _get_format(hs)
        significance = _get_match_significance(hs)
        status = _get_match_status(hs)
        has_scorebot = hs('#scoreboardElement').exists()
        stats_id = _get_stats_id(hs)
        team1 = _get_team(hs, 1)
        team2 = _get_team(hs, 2)
        vetoes = _get_vetoes(hs, team1, team2)
        event = _get_event(hs)
        odds = _get_odds(hs)
        community_odds = _get_community_odds(hs)
        maps = _get_maps(hs)
        players = _get_players(hs)
        streams = _get_streams(hs)
        demos = _get_demos(hs)
        highlighted_players = _get_highlighted_players(hs)
        head_to_head = _get_head_to_head(hs)
        highlights = _get_highlights(hs, team1, team2)
        player_of_the_match = _get_player_of_the_match(hs, players)
        winner_team = _get_winner_team(hs, team1, team2)

        return FullMatch(
            id=match_id,
            statsId=stats_id,
            title=title,
            date=date,
            significance=significance,
            format=format_info,
            status=status,
            hasScorebot=has_scorebot,
            team1=team1,
            team2=team2,
            winnerTeam=winner_team,
            vetoes=vetoes,
            event=event,
            odds=odds + ([community_odds] if community_odds else []),
            maps=maps,
            players=players,
            streams=streams,
            demos=demos,
            highlightedPlayers=highlighted_players,
            headToHead=head_to_head,
            highlights=highlights,
            playerOfTheMatch=player_of_the_match
        )
    return inner

# ---------- 内部解析函数 ----------


def _get_match_status(hs) -> MatchStatus:
    text = hs('.countdown').trim_text() or ''
    if 'LIVE' in text:
        return MatchStatus.Live
    if 'Match postponed' in text:
        return MatchStatus.Postponed
    if 'Match deleted' in text:
        return MatchStatus.Deleted
    if 'Match over' in text:
        return MatchStatus.Over
    return MatchStatus.Scheduled


def _get_team(hs, n: int) -> Optional[FullMatchTeam]:
    sel = f'.team{n}-gradient'
    if not hs(sel).exists():
        return None
    name = hs(f'{sel} .teamName').text()
    id = hs(f'{sel} a').attr_then('href', lambda h: get_id_at(2, h))
    rank_el = hs('.teamRanking a').eq(n - 1).contents().eq(1)
    rank = None
    if rank_el.exists():
        rank_text = rank_el.text().replace('#', '')
        rank = parse_number(rank_text)
    return FullMatchTeam(name=name, id=id, rank=rank)


def _get_vetoes(hs, team1: Optional[Team], team2: Optional[Team]) -> List[Veto]:
    if not team1 or not team2:
        return []

    def parse_veto(text: str) -> Veto:
        # 移除可能的行号 "1. "
        clean = text.replace('\n', ' ').strip()
        if clean.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
            clean = clean.split(' ', 1)[-1]
        if 'picked' in clean or 'removed' in clean:
            parts = clean.split(' ', 1)
            team_name = parts[0].strip()
            action = 'picked' if 'picked' in clean else 'removed'
            map_raw = clean.split(action)[-1].strip()
            map_enum = from_map_name(map_raw) if map_raw else GameMap.Default
            team = next((t for t in [team1, team2]
                        if t.name == team_name), None)
            return Veto(team=team, map=map_enum, type=action)
        else:
            parts = clean.split(' ')
            map_enum = from_map_name(parts[1]) if len(
                parts) > 1 else GameMap.Default
            return Veto(map=map_enum, type='leftover')

    vetoes = []
    # 新版格式
    if hs('.veto-box').length > 1:
        for el in hs('.veto-box').last().find('.padding div').to_array():
            vetoes.append(parse_veto(el.text()))
        return vetoes
    # 旧版格式
    first_box = hs('.veto-box').first()
    if first_box.exists():
        lines = first_box.lines()
        veto_idx = next((i for i, line in enumerate(
            lines) if 'Veto process' in line), -1)
        if veto_idx >= 0:
            for line in lines[veto_idx + 2:-1]:
                if line.strip():
                    vetoes.append(parse_veto(line))
    return vetoes


def _get_event(hs) -> Event:
    name = hs('.timeAndEvent .event a').text()
    id = hs('.timeAndEvent .event a').attr_then(
        'href', lambda h: get_id_at(2, h))
    return Event(name=name, id=id)


def _get_odds(hs) -> List[ProviderOdds]:
    odds = []
    for el in hs('tr.provider:not(.hidden)').to_array():
        if el.find('.noOdds').exists():
            continue
        provider = el.find('td').first().find(
            'a img').first().attr('title') or ''
        t1_text = el.find(
            '.odds-cell').first().find('a').text().replace('%', '')
        t2_text = el.find(
            '.odds-cell').last().find('a').text().replace('%', '')
        t1 = float(t1_text) if t1_text else 0
        t2 = float(t2_text) if t2_text else 0
        if '%' in el.find('.odds-cell').first().text():
            t1 = percentage_to_decimal_odd(t1)
            t2 = percentage_to_decimal_odd(t2)
        odds.append(ProviderOdds(provider=provider, team1=t1, team2=t2))
    return odds


def _get_community_odds(hs) -> Optional[ProviderOdds]:
    if not hs('.pick-a-winner').exists():
        return None
    t1_str = hs(
        '.pick-a-winner-team.team1 > .percentage').first().text().replace('%', '')
    t2_str = hs(
        '.pick-a-winner-team.team2 > .percentage').first().text().replace('%', '')
    t1 = float(t1_str) if t1_str else 0
    t2 = float(t2_str) if t2_str else 0
    return ProviderOdds(
        provider='community',
        team1=percentage_to_decimal_odd(t1),
        team2=percentage_to_decimal_odd(t2)
    )


def _get_maps(hs) -> List[MapResult]:
    results = []
    for map_el in hs('.mapholder').to_array():
        name = from_map_name(map_el.find('.mapname').text())
        t1 = parse_number(map_el.find(
            '.results-left .results-team-score').trim_text() or '0') or 0
        t2 = parse_number(map_el.find(
            '.results-right .results-team-score').trim_text() or '0') or 0
        stats_id = None
        stats_el = map_el.find('.results-stats')
        if stats_el.exists():
            href = stats_el.attr('href') or ''
            parts = href.split('/')
            if len(parts) > 4:
                stats_id = parse_number(parts[4])

        result = None
        if t1 is not None and t2 is not None:
            halfs_str = map_el.find(
                '.results-center-half-score').trim_text() or ''
            halfs = []
            if halfs_str:
                parts = [x.replace('(', '').replace(')', '').replace(
                    ';', '') for x in halfs_str.split(' ')]
                for half in parts:
                    scores = half.split(':')
                    if len(scores) == 2:
                        halfs.append(MapHalfResult(
                            team1Rounds=parse_number(scores[0]) or 0,
                            team2Rounds=parse_number(scores[1]) or 0
                        ))
            if len(halfs) < 2:
                halfs = [MapHalfResult(), MapHalfResult()]
            result = MapResultData(team1TotalRounds=t1,
                                   team2TotalRounds=t2, halfResults=halfs)
        results.append(MapResult(name=name, result=result, statsId=stats_id))
    return results


def _get_players(hs) -> dict:
    def parse_player(player_el) -> Player:
        name = player_el.find('.text-ellipsis').text()
        id = parse_number(player_el.data('player-id'))
        return Player(name=name, id=id)

    team1 = []
    for el in hs('div.players').first().find('tr').last().find('.flagAlign').to_array():
        team1.append(parse_player(el))
    team2 = []
    for el in hs('div.players').eq(1).find('tr').last().find('.flagAlign').to_array():
        team2.append(parse_player(el))
    return {'team1': team1, 'team2': team2}


def _get_streams(hs) -> List[Stream]:
    streams = []
    for el in hs('.stream-box').to_array():
        if not el.find('.stream-flag').exists() and not el.attr('data-demo-link-button'):
            continue
        name = el.find('.stream-box-embed').text() or 'VOD'
        link = el.data(
            'stream-embed') or el.find('.stream-box-embed').attr('data-stream-embed')
        viewers = el.find('.viewers.gtSmartphone-only').num_from_text() or -1
        streams.append(Stream(name=name, link=link, viewers=viewers))
    if hs('.stream-box.hltv-live').exists():
        streams.append(Stream(
            name='HLTV Live',
            link=hs('.stream-box.hltv-live a').attr('href') or '',
            viewers=-1
        ))
    gotv_el = hs('[data-demo-link-button]')
    if gotv_el.exists():
        link = 'https://www.hltv.org' + gotv_el.data('demo-link')
        streams.append(Stream(name='GOTV', link=link, viewers=-1))
    return streams


def _get_demos(hs) -> List[Demo]:
    demos = []
    for demo_el in hs('[class="stream-box"]:not(:has(.stream-box-embed))').to_array():
        demo_link = demo_el.attr('data-demo-link')
        if demo_link:
            demos.append(Demo(name='GOTV Demo', link=demo_link))
        else:
            name = demo_el.text()
            link = demo_el.attr('data-stream-embed')
            if link:
                demos.append(Demo(name=name, link=link))
    return [d for d in demos if d.link]


def _get_highlighted_players(hs) -> Optional[dict]:
    left = hs('.lineups-compare-left .lineups-compare-player-links a').first()
    right = hs('.lineups-compare-right .lineups-compare-player-links a').first()
    if not left.exists() or not right.exists():
        return None
    return {
        'team1': Player(
            name=hs('.lineups-compare-left .lineups-compare-playername').text(),
            id=left.attr_then('href', lambda h: get_id_at(2, h))
        ),
        'team2': Player(
            name=hs('.lineups-compare-right .lineups-compare-playername').text(),
            id=right.attr_then('href', lambda h: get_id_at(2, h))
        )
    }


def _get_head_to_head(hs) -> List[HeadToHeadResult]:
    results = []
    for match_el in hs('.head-to-head-listing tr').to_array():
        date = parse_number(match_el.find('.date a span').attr('data-unix'))
        map_text = match_el.find('.dynamic-map-name-short').text()
        map_enum = from_map_name(map_text)
        winner = None
        winner_el = match_el.find('.winner')
        if winner_el.exists():
            winner_name = winner_el.find('.flag').next().text()
            winner_id = winner_el.find('.flag').next().attr_then(
                'href', lambda h: get_id_at(2, h))
            winner = Team(name=winner_name, id=winner_id)
        event_name = match_el.find('.event a').text()
        event_id = match_el.find('.event a').attr_then(
            'href', lambda h: get_id_at(2, h))
        result_text = match_el.find('.result').text()
        results.append(HeadToHeadResult(
            date=date,
            winner=winner,
            event=Event(name=event_name, id=event_id),
            map=map_enum,
            result=result_text
        ))
    return results


def _get_highlights(hs, team1, team2) -> List[Highlight]:
    if not team1 or not team2:
        return []
    return [
        Highlight(link=el.attr('data-highlight-embed'), title=el.text())
        for el in hs('.highlight').to_array()
    ]


def _get_stats_id(hs) -> Optional[int]:
    stats_el = hs('.stats-detailed-stats a')
    if stats_el.exists() and 'mapstats' not in (stats_el.attr('href') or ''):
        return get_id_at(3, stats_el.attr('href'))
    return None


def _get_player_of_the_match(hs, players) -> Optional[Player]:
    name_el = hs('.highlighted-player .player-nick')
    if not name_el.exists():
        return None
    name = name_el.text()
    for p in players['team1'] + players['team2']:
        if p.name == name:
            return p
    return None


def _get_winner_team(hs, team1, team2) -> Optional[FullMatchTeam]:
    if hs('.team1-gradient .won').exists():
        return team1
    if hs('.team2-gradient .won').exists():
        return team2
    return None


def _get_format(hs) -> Optional[dict]:
    fmt_el = hs('.preformatted-text')
    if not fmt_el.exists():
        return None
    line = fmt_el.lines()[0].strip()
    parts = line.split(' (')
    format_type = from_full_match_format(parts[0])
    location = None
    if len(parts) > 1:
        location_str = parts[1].rstrip(')')
        if location_str in ('LAN', 'Online'):
            location = MatchFormatLocation(location_str)
    return {'type': format_type, 'location': location}


def _get_match_significance(hs) -> Optional[str]:
    lines = hs('.preformatted-text').lines()
    for line in lines:
        if line.strip().startswith('*'):
            return line.strip().lstrip('*').strip()
    return None
