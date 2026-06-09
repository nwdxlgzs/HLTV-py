from dataclasses import dataclass
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.country import Country
from ..shared.event_type import EventType
from ..utils import fetch_page, get_id_at, parse_number
from ..scraper import HLTVScraper


@dataclass
class EventPreview:
    id: int
    name: str
    dateStart: int
    dateEnd: int
    numberOfTeams: Optional[int] = None
    prizePool: Optional[str] = None
    location: Optional[Country] = None
    featured: bool = False


@dataclass
class GetEventsArguments:
    eventType: Optional[EventType] = None
    prizePoolMin: Optional[int] = None
    prizePoolMax: Optional[int] = None
    attendingTeamIds: Optional[List[int]] = None
    attendingPlayerIds: Optional[List[int]] = None


def get_events(config: HLTVConfig) -> Callable[[Optional[GetEventsArguments]], Awaitable[List[EventPreview]]]:
    async def inner(options: Optional[GetEventsArguments] = None) -> List[EventPreview]:
        options = options or GetEventsArguments()
        query = {}
        if options.eventType:
            query['eventType'] = options.eventType.value
        if options.prizePoolMin:
            query['prizeMin'] = options.prizePoolMin
        if options.prizePoolMax:
            query['prizeMax'] = options.prizePoolMax
        if options.attendingTeamIds:
            query['team'] = options.attendingTeamIds
        if options.attendingPlayerIds:
            query['player'] = options.attendingPlayerIds
        query_string = urlencode(query, doseq=True)
        soup = await fetch_page(f'https://www.hltv.org/events?{query_string}', config.load_page)
        hs = HLTVScraper(soup)

        # 特色赛事ID
        featured_ids = [
            el.attr_then('href', lambda h: get_id_at(2, h))
            for el in hs('.tab-content[id="FEATURED"] a.ongoing-event').to_array()
        ]

        events = []

        # 进行中赛事
        for el in hs('.tab-content[id="ALL"] a.ongoing-event').to_array():
            eid = el.attr_then('href', lambda h: get_id_at(2, h))
            if eid:
                events.append(EventPreview(
                    id=eid,
                    name=el.find('.event-name-small .text-ellipsis').text(),
                    dateStart=el.find(
                        'tr.eventDetails span[data-unix]').first().num_from_attr('data-unix') or 0,
                    dateEnd=el.find(
                        'tr.eventDetails span[data-unix]').last().num_from_attr('data-unix') or 0,
                    featured=eid in featured_ids
                ))

        # 大型即将举行赛事
        for el in hs('a.big-event').to_array():
            eid = el.attr_then('href', lambda h: get_id_at(2, h))
            if not eid:
                continue
            loc_name = el.find('.big-event-location').text()
            location = None
            if loc_name != 'TBA':
                flag_src = el.find('.location-top-teams img.flag').attr('src')
                location = Country(
                    name=loc_name,
                    code=flag_src.split(
                        '/')[-1].split('.')[0] if flag_src else ''
                )
            events.append(EventPreview(
                id=eid,
                name=el.find('.big-event-name').text(),
                dateStart=el.find(
                    '.additional-info .col-date span[data-unix]').first().num_from_attr('data-unix') or 0,
                dateEnd=el.find(
                    '.additional-info .col-date span[data-unix]').last().num_from_attr('data-unix') or 0,
                location=location,
                prizePool=el.find(
                    '.additional-info tr').first().find('td').eq(1).text(),
                numberOfTeams=parse_number(
                    el.find('.additional-info tr').first().find('td').eq(2).text()),
                featured=True
            ))

        # 小型即将举行赛事
        for el in hs('a.small-event').to_array():
            eid = el.attr_then('href', lambda h: get_id_at(2, h))
            if not eid:
                continue
            loc_text = el.find(
                '.smallCountry .col-desc').text().replace(' | ', '')
            flag_src = el.find('.smallCountry img.flag').attr('src')
            location = Country(
                name=loc_text,
                code=flag_src.split('/')[-1].split('.')[0] if flag_src else ''
            )
            events.append(EventPreview(
                id=eid,
                name=el.find('.table tr').first().find(
                    'td').first().find('.text-ellipsis').text(),
                dateStart=el.find(
                    'td span[data-unix]').first().num_from_attr('data-unix') or 0,
                dateEnd=el.find(
                    'td span[data-unix]').last().num_from_attr('data-unix') or 0,
                location=location,
                prizePool=el.find('.prizePoolEllipsis').text(),
                numberOfTeams=parse_number(
                    el.find('.prizePoolEllipsis').prev().text()),
                featured=False
            ))

        return events
    return inner
