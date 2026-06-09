from ..utils import parse_number
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..utils import fetch_page, get_id_at
from ..scraper import HLTVScraper
from ..shared.team import Team
from ..shared.event import Event


class MatchEventType(Enum):
    All = 'All'
    LAN = 'Lan'
    Online = 'Online'


class MatchFilter(Enum):
    LanOnly = 'lan_only'
    TopTier = 'top_tier'


@dataclass
class GetMatchesArguments:
    eventIds: Optional[List[int]] = None
    eventType: Optional[MatchEventType] = None
    filter: Optional[MatchFilter] = None
    teamIds: Optional[List[int]] = None


@dataclass
class MatchPreview:
    id: int = 0
    team1: Optional[Team] = None
    team2: Optional[Team] = None
    date: Optional[int] = None
    format: Optional[str] = None
    event: Optional[Event] = None
    title: Optional[str] = None
    live: bool = False
    stars: int = 0


def get_matches(config: HLTVConfig) -> Callable[[Optional[GetMatchesArguments]], Awaitable[List[MatchPreview]]]:
    async def inner(args: Optional[GetMatchesArguments] = None) -> List[MatchPreview]:
        args = args or GetMatchesArguments()
        query = {}
        if args.eventIds:
            query['event'] = args.eventIds
        if args.eventType:
            query['eventType'] = args.eventType.value
        if args.filter:
            query['predefinedFilter'] = args.filter.value
        if args.teamIds:
            query['team'] = args.teamIds
        query_string = urlencode(query, doseq=True)
        url = f'https://www.hltv.org/matches?{query_string}'
        soup = await fetch_page(url, config.load_page)
        hs = HLTVScraper(soup)

        # 收集赛事名称供后续匹配
        events_dict = {}
        for el in hs('.event-filter-popup a').to_array():
            eid = el.attr_then('href', lambda h: int(h.split('=')[-1]))
            name = el.find('.event-name').text()
            if eid:
                events_dict[name] = eid
        for el in hs('.events-container a').to_array():
            eid = el.attr_then('href', lambda h: int(h.split('=')[-1]))
            name = el.find('.featured-event-tooltip-content').text()
            if eid:
                events_dict[name] = eid

        matches = []
        all_els = hs('.liveMatch-container').to_array() + \
            hs('.upcomingMatch').to_array()
        for el in all_els:
            id = el.find('.a-reset').attr_then('href',
                                               lambda h: get_id_at(2, h)) or 0
            stars = 5 - el.find('.matchRating i.faded').length
            live = el.find('.matchTime.matchLive').text() == 'LIVE'
            title = el.find('.matchInfoEmpty').text() or None
            date = el.find('.matchTime').num_from_attr('data-unix')

            team1 = None
            team2 = None
            if not title:
                team1_name = el.find('.matchTeamName').first(
                ).text() or el.find('.team1 .team').text()
                team1_id = parse_number(el.attr('team1'))
                team2_name = el.find('.matchTeamName').eq(
                    1).text() or el.find('.team2 .team').text()
                team2_id = parse_number(el.attr('team2'))
                team1 = Team(name=team1_name, id=team1_id)
                team2 = Team(name=team2_name, id=team2_id)

            format_str = el.find('.matchMeta').text()
            event_name = el.find('.matchEventLogo').attr('title')
            event = None
            if event_name and event_name in events_dict:
                event = Event(name=event_name, id=events_dict[event_name])

            matches.append(MatchPreview(
                id=id,
                team1=team1,
                team2=team2,
                date=date,
                format=format_str,
                event=event,
                title=title,
                live=live,
                stars=stars
            ))
        return matches
    return inner


# 需要在 get_matches 内部使用 parse_number，导入一下
