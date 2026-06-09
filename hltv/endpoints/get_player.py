from dataclasses import dataclass, field
from typing import List, Optional, Callable, Awaitable
from ..config import HLTVConfig
from ..shared.article import Article
from ..shared.country import Country
from ..shared.event import Event
from ..shared.team import Team
from ..utils import fetch_page, generate_random_suffix, get_id_at, parse_number
from ..scraper import HLTVScraper


@dataclass
class FullPlayerTeam(Team):
    startDate: Optional[int] = None
    leaveDate: Optional[int] = None
    trophies: List[Event] = field(default_factory=list)


@dataclass
class PlayerAchievement:
    event: Optional[Event] = None
    place: str = ''


@dataclass
class FullPlayer:
    id: int
    name: Optional[str] = None
    ign: str = ''
    image: Optional[str] = None
    age: Optional[int] = None
    country: Optional[Country] = None
    team: Optional[Team] = None
    twitter: Optional[str] = None
    twitch: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    statistics: Optional[dict] = None
    teams: List[FullPlayerTeam] = field(default_factory=list)
    achievements: List[PlayerAchievement] = field(default_factory=list)
    news: List[Article] = field(default_factory=list)


def get_player(config: HLTVConfig) -> Callable[[dict], Awaitable[FullPlayer]]:
    async def inner(params: dict) -> FullPlayer:
        player_id = params['id']
        soup = await fetch_page(
            f'https://www.hltv.org/player/{player_id}/{generate_random_suffix()}',
            config.load_page
        )
        hs = HLTVScraper(soup)

        name_text = hs('.playerRealname').trim_text()
        name = name_text if name_text != '-' else None
        ign = hs('.playerNickname').text()
        image_url = hs(
            '.profile-img').attr('src') or hs('.bodyshot-img').attr('src')
        if image_url and ('bodyshot/unknown.png' in image_url or 'player_silhouette.png' in image_url):
            image_url = None

        age = hs('.playerAge .listRight').text()
        age = parse_number(age.split(' ')[0]) if age else None

        twitter = hs('.twitter').parent().attr('href')
        twitch = hs('.twitch').parent().attr('href')
        facebook = hs('.facebook').parent().attr('href')
        instagram = hs('.instagram').parent().attr('href')

        flag = hs('.playerRealname .flag')
        country = Country(
            name=flag.attr('alt') or '',
            code=flag.attr_then('src', lambda x: x.split(
                '/')[-1].split('.')[0]) or ''
        )

        team = None
        team_text = hs('.playerTeam .listRight').trim_text()
        if team_text and team_text != 'No team':
            team_name = hs('.playerTeam a').trim_text() or ''
            team_id = hs('.playerTeam a').attr_then(
                'href', lambda h: get_id_at(2, h))
            team = Team(name=team_name, id=team_id)

        # 统计
        statistics = None
        if not hs('.playerpage-container.empty-state').exists():
            def get_stat(i: int) -> float:
                try:
                    return float(hs('.playerpage-container .player-stat').eq(i).find('.statsVal').text().replace('%', ''))
                except:
                    return 0.0
            statistics = {
                'rating': get_stat(0),
                'killsPerRound': get_stat(1),
                'headshots': get_stat(2),
                'mapsPlayed': int(get_stat(3)),
                'deathsPerRound': get_stat(4),
                'roundsContributed': int(get_stat(5)),
            }

        # 成就
        achievements = []
        for el in hs('.achievement-table .team').to_array():
            achievements.append(PlayerAchievement(
                place=el.find('.achievement').text(),
                event=Event(
                    name=el.find('.tournament-name-cell a').text(),
                    id=el.find(
                        '.tournament-name-cell a').attr_then('href', lambda h: get_id_at(2, h))
                )
            ))

        # 队伍经历
        teams = []
        for el in hs('.team-breakdown .team').to_array():
            team_id = el.find(
                '.team-name-cell a').attr_then('href', lambda h: get_id_at(2, h))
            team_name = el.find('.team-name').text()
            start_date = el.find(
                '.time-period-cell [data-unix]').first().num_from_attr('data-unix')
            leave_date = el.find(
                '.time-period-cell [data-unix]').eq(1).num_from_attr('data-unix')
            trophies = []
            for trophy_el in el.find('.trophy-row-trophy a').to_array():
                trophies.append(Event(
                    id=trophy_el.attr_then('href', lambda h: get_id_at(2, h)),
                    name=trophy_el.find('img').attr('title') or ''
                ))
            teams.append(FullPlayerTeam(
                name=team_name, id=team_id,
                startDate=start_date, leaveDate=leave_date,
                trophies=trophies
            ))

        # 新闻
        news = []
        for el in hs('#newsBox a').to_array():
            news.append(Article(
                name=el.contents().eq(1).text(),
                link=el.attr('href') or ''
            ))

        return FullPlayer(
            id=player_id,
            name=name,
            ign=ign,
            image=image_url,
            age=age,
            twitter=twitter,
            twitch=twitch,
            facebook=facebook,
            instagram=instagram,
            country=country,
            team=team,
            statistics=statistics,
            achievements=achievements,
            teams=teams,
            news=news
        )
    return inner
