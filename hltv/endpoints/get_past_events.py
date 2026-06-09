from dataclasses import dataclass
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.country import Country
from ..shared.event_type import EventType, from_text
from ..utils import fetch_page, get_id_at, parse_number, sleep
from ..scraper import HLTVScraper


@dataclass
class PastEventPreview:
    id: int
    type: EventType
    name: str
    dateStart: int
    dateEnd: int
    numberOfTeams: int
    prizePool: str
    location: Country


@dataclass
class GetPastEventsArguments:
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    eventType: Optional[EventType] = None
    prizePoolMin: Optional[int] = None
    prizePoolMax: Optional[int] = None
    attendingTeamIds: Optional[List[int]] = None
    attendingPlayerIds: Optional[List[int]] = None
    delayBetweenPageRequests: int = 0


def get_past_events(config: HLTVConfig) -> Callable[[GetPastEventsArguments], Awaitable[List[PastEventPreview]]]:
    async def inner(options: GetPastEventsArguments) -> List[PastEventPreview]:
        query = {}
        if options.startDate:
            query['startDate'] = options.startDate
        if options.endDate:
            query['endDate'] = options.endDate
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

        page = 0
        all_events: List[PastEventPreview] = []

        while True:
            await sleep(options.delayBetweenPageRequests)
            url = f'https://www.hltv.org/events/archive?{query_string}&offset={page * 50}'
            soup = await fetch_page(url, config.load_page)
            hs = HLTVScraper(soup)
            page_events = hs('a.small-event').to_array()
            if not page_events:
                break

            for el in page_events:
                eid = el.attr_then('href', lambda h: get_id_at(2, h))
                if not eid:
                    continue
                name = el.find('.table tr').first().find(
                    'td').first().find('.text-ellipsis').text()
                type_str = el.find('.table tr').first().find(
                    'td').last().text()
                event_type = from_text(type_str) or EventType.Other
                date_start = el.find(
                    'td span[data-unix]').first().num_from_attr('data-unix') or 0
                date_end = el.find(
                    'td span[data-unix]').last().num_from_attr('data-unix') or 0
                loc_name = el.find(
                    '.smallCountry .col-desc').text().replace(' | ', '')
                flag_src = el.find('.smallCountry img.flag').attr('src')
                location = Country(
                    name=loc_name,
                    code=flag_src.split(
                        '/')[-1].split('.')[0] if flag_src else ''
                )
                prize_pool = el.find('.prizePoolEllipsis').text()
                num_teams_str = el.find(
                    '.prizePoolEllipsis').prev().text().replace('+', '')
                num_teams = int(num_teams_str) if num_teams_str else 0
                all_events.append(PastEventPreview(
                    id=eid,
                    type=event_type,
                    name=name,
                    dateStart=date_start,
                    dateEnd=date_end,
                    numberOfTeams=num_teams,
                    prizePool=prize_pool,
                    location=location
                ))
            page += 1
        return all_events
    return inner
