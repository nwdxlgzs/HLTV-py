from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable, Awaitable
from ..config import HLTVConfig
from ..shared.article import Article
from ..shared.country import Country
from ..shared.player import Player
from ..utils import fetch_page, generate_random_suffix, get_id_at, parse_number
from ..scraper import HLTVScraper


class TeamPlayerType(Enum):
    Coach = 'Coach'
    Starter = 'Starter'
    Substitute = 'Substitute'
    Benched = 'Benched'


@dataclass
class FullTeamPlayer(Player):
    type: Optional[TeamPlayerType] = None
    timeOnTeam: str = ''
    mapsPlayed: int = 0


@dataclass
class FullTeam:
    id: int
    name: str
    logo: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    country: Optional[Country] = None
    rank: Optional[int] = None
    players: List[FullTeamPlayer] = field(default_factory=list)
    rankingDevelopment: List[int] = field(default_factory=list)
    news: List[Article] = field(default_factory=list)


def _get_player_type(text: str) -> Optional[TeamPlayerType]:
    if text == 'STARTER':
        return TeamPlayerType.Starter
    if text == 'BENCHED':
        return TeamPlayerType.Benched
    if text == 'SUBSTITUTE':
        return TeamPlayerType.Substitute
    return None


def get_team(config: HLTVConfig) -> Callable[[dict], Awaitable[FullTeam]]:
    async def inner(params: dict) -> FullTeam:
        team_id = params['id']
        soup = await fetch_page(
            f'https://www.hltv.org/team/{team_id}/{generate_random_suffix()}',
            config.load_page
        )
        hs = HLTVScraper(soup)

        name = hs('.profile-team-name').text()
        logoSrc = hs('.teamlogo').attr('src')
        logo = logoSrc if logoSrc and 'placeholder.svg' not in logoSrc else None
        facebook = hs('.facebook').parent().attr('href')
        twitter = hs('.twitter').parent().attr('href')
        instagram = hs('.instagram').parent().attr('href')
        rank_text = hs(
            '.profile-team-stat .right').first().text().replace('#', '')
        rank = parse_number(rank_text)

        # 解析队员
        players = []
        for el in hs('.players-table tbody tr').to_array():
            player_id = el.find(
                '.playersBox-playernick-image').attr_then('href', lambda h: get_id_at(2, h))
            player_name = el.find(
                '.playersBox-playernick-image .playersBox-playernick .text-ellipsis').text()
            time_on_team = el.find('td').eq(2).trim_text() or ''
            maps_played = el.find('td').eq(3).num_from_text() or 0
            ptype = _get_player_type(el.find('.player-status').text())
            players.append(FullTeamPlayer(
                name=player_name, id=player_id,
                type=ptype, timeOnTeam=time_on_team, mapsPlayed=maps_played
            ))

        # 教练
        coach_table = hs('.coach-table')
        if coach_table.exists():
            coach_id = coach_table.find(
                '.playersBox-playernick-image').attr_then('href', lambda h: get_id_at(2, h))
            coach_name = coach_table.find(
                '.playersBox-playernick-image .playersBox-playernick .text-ellipsis').text()
            time = coach_table.find('tbody tr').first().find(
                'td').eq(1).trim_text() or ''
            maps = coach_table.find('tbody tr').first().find(
                'td').eq(2).num_from_text() or 0
            players.append(FullTeamPlayer(
                name=coach_name, id=coach_id,
                type=TeamPlayerType.Coach, timeOnTeam=time, mapsPlayed=maps
            ))

        # 排名历史
        ranking_development = []
        try:
            graph_config = hs('.graph').attr('data-fusionchart-config')
            if graph_config:
                import json
                config_data = json.loads(graph_config)
                dataset = config_data['dataSource']['dataset'][0]['data']
                ranking_development = [parse_number(
                    item['value']) or 0 for item in dataset]
        except Exception:
            pass

        # 国家
        flag = hs('.team-country .flag')
        country = Country(
            name=flag.attr('alt') or '',
            code=flag.attr_then('src', lambda x: x.split(
                '/')[-1].split('.')[0]) or ''
        )

        # 新闻
        news = []
        for el in hs('#newsBox a').to_array():
            news.append(Article(
                name=el.contents().eq(1).text(),
                link=el.attr('href') or ''
            ))

        return FullTeam(
            id=team_id,
            name=name,
            logo=logo,
            facebook=facebook,
            twitter=twitter,
            instagram=instagram,
            country=country,
            rank=rank,
            players=players,
            rankingDevelopment=ranking_development,
            news=news
        )
    return inner
