from typing import Callable, Awaitable
from ..config import HLTVConfig
from .get_event import FullEvent, get_event


def get_event_by_name(config: HLTVConfig) -> Callable[[dict], Awaitable[FullEvent]]:
    async def inner(params: dict) -> FullEvent:
        name = params['name']
        import json
        page_content = json.loads(await config.load_page(f'https://www.hltv.org/search?term={name}'))
        first_result = page_content[0]['events'][0]
        if not first_result:
            raise Exception(f'Event {name} not found')
        return await get_event(config)({'id': first_result['id']})
    return inner
