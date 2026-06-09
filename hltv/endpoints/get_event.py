from dataclasses import dataclass, field
from typing import List, Optional, Callable, Awaitable
from ..config import HLTVConfig
from ..shared.article import Article
from ..shared.country import Country
from ..shared.event import Event
from ..shared.game_map import from_map_name, GameMap
from ..shared.team import Team
from ..utils import fetch_page, generate_random_suffix, get_id_at, not_null, parse_number
from ..scraper import HLTVScraper


@dataclass
class FullEventTeam(Team):
    reasonForParticipation: Optional[str] = None
    rankDuringEvent: Optional[int] = None


@dataclass
class FullEventPrizeDistribution:
    place: str = ''
    prize: Optional[str] = None
    otherPrize: Optional[str] = None
    qualifiesFor: Optional[Event] = None
    team: Optional[Team] = None


@dataclass
class FullEventFormat:
    type: str = ''
    description: str = ''


@dataclass
class FullEventHighlight:
    link: str = ''
    name: str = ''
    views: int = 0
    thumbnail: str = ''
    team1: Optional[Team] = None
    team2: Optional[Team] = None


@dataclass
class FullEvent:
    id: int
    name: str
    logo: str = ''
    dateStart: Optional[int] = None
    dateEnd: Optional[int] = None
    prizePool: str = ''
    location: Optional[Country] = None
    numberOfTeams: Optional[int] = None
    teams: List[FullEventTeam] = field(default_factory=list)
    prizeDistribution: List[FullEventPrizeDistribution] = field(
        default_factory=list)
    relatedEvents: List[Event] = field(default_factory=list)
    formats: List[FullEventFormat] = field(default_factory=list)
    mapPool: List[GameMap] = field(default_factory=list)
    highlights: List[FullEventHighlight] = field(default_factory=list)
    news: List[Article] = field(default_factory=list)


def get_event(config: HLTVConfig) -> Callable[[dict], Awaitable[FullEvent]]:
    async def inner(params: dict) -> FullEvent:
        event_id = params['id']
        soup = await fetch_page(
            f'https://www.hltv.org/events/{event_id}/{generate_random_suffix()}',
            config.load_page
        )
        hs = HLTVScraper(soup)

        name = hs('.event-hub-title').text()
        logo = hs('.sidebar-first-level').find('.event-logo').attr('src') or ''
        prize_pool = hs('td.prizepool').text()
        date_start = hs(
            'td.eventdate span[data-unix]').first().num_from_attr('data-unix')
        date_end = hs(
            'td.eventdate span[data-unix]').last().num_from_attr('data-unix')
        location = Country(
            name=hs('.location span.text-ellipsis').text(),
            code=hs('img.flag').attr_then(
                'src', lambda x: x.split('/')[-1].split('.')[0]) or ''
        )

        # 相关赛事
        related_events = []
        for el in hs('.related-event').to_array():
            related_events.append(Event(
                name=el.find('.event-name').text(),
                id=el.find('a').attr_then('href', lambda h: get_id_at(2, h))
            ))

        # 奖金分配
        prize_distribution = []
        for el in hs('.placements .placement').to_array():
            other_prize = el.find(
                '.spot-prize').text() or el.find('.prize').first().next().text() or None
            qualifies_for = None
            if other_prize:
                for ev in related_events:
                    if ev.name == other_prize:
                        qualifies_for = ev
                        break
            team_el = el.find('.team').children()
            team = None
            if team_el.exists():
                team = Team(
                    name=el.find('.team a').text(),
                    id=el.find('.team a').attr_then(
                        'href', lambda h: get_id_at(2, h))
                )
            prize_distribution.append(FullEventPrizeDistribution(
                place=el.children().eq(1).text(),
                prize=el.find('.prize').first().text() or None,
                qualifiesFor=qualifies_for,
                otherPrize=None if qualifies_for else other_prize,
                team=team
            ))

        # 参赛队伍数量
        number_of_teams = hs('td.teamsNumber').num_from_text()

        # 参赛队伍
        teams = []
        for el in hs('.team-box').to_array():
            if not el.find('.team-name a').exists():
                continue
            rank_text = el.find('.event-world-rank').text().replace('#', '')
            teams.append(FullEventTeam(
                name=el.find('.logo').attr('title'),
                id=el.find('.team-name a').attr_then('href',
                                                     lambda h: get_id_at(2, h)),
                reasonForParticipation=el.find('.sub-text').trim_text(),
                rankDuringEvent=parse_number(rank_text)
            ))

        # 格式
        formats = []
        for el in hs('.formats tr').to_array():
            formats.append(FullEventFormat(
                type=el.find('.format-header').text(),
                description=el.find(
                    '.format-data').text().replace('\n', ' ').strip()
            ))

        # 地图池
        map_pool = []
        for el in hs('.map-pool-map-holder').to_array():
            map_pool.append(from_map_name(
                el.find('.map-pool-map-name').text()))

        # 精彩集锦
        highlights = []
        for el in hs('.highlight-video').to_array():
            video_name = el.find('.video-discription-text').text()
            video_link = el.data('mp4-url')
            thumb_base = el.data('thumbnail').split('-preview-')[0]
            thumbnail = f'{thumb_base}-preview.jpg'
            team1_name = el.find(
                '.video-team').first().find('.video-team-img').first().attr('title')
            team1 = next((t for t in teams if t.name == team1_name), None)
            team2_name = el.find(
                '.video-team').last().find('.video-team-img').first().attr('title')
            team2 = next((t for t in teams if t.name == team2_name), None)
            views_text = el.find('.thumbnail-view-count').text().split(' ')[0]
            views = int(views_text) if views_text else 0
            highlights.append(FullEventHighlight(
                name=video_name,
                link=video_link,
                thumbnail=thumbnail,
                views=views,
                team1=Team(id=team1.id if team1 else None,
                           name=team1.name if team1 else team1_name),
                team2=Team(id=team2.id if team2 else None,
                           name=team2.name if team2 else team2_name)
            ))

        # 新闻
        news = []
        for el in hs('.news .item').to_array():
            news.append(Article(
                name=el.find('.flag-align .text-ellipsis').text(),
                link=el.find('a').attr('href') or ''
            ))

        return FullEvent(
            id=event_id,
            name=name,
            logo=logo,
            dateStart=date_start,
            dateEnd=date_end,
            prizePool=prize_pool,
            location=location,
            numberOfTeams=number_of_teams,
            teams=teams,
            prizeDistribution=prize_distribution,
            relatedEvents=related_events,
            formats=formats,
            mapPool=map_pool,
            highlights=highlights,
            news=news
        )
    return inner
