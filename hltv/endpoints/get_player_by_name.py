from typing import Callable, Awaitable
from ..config import HLTVConfig
from .get_player import FullPlayer, get_player


def get_player_by_name(config: HLTVConfig) -> Callable[[dict], Awaitable[FullPlayer]]:
    async def inner(params: dict) -> FullPlayer:
        name = params['name']
        import json
        page_content = json.loads(await config.load_page(f'https://www.hltv.org/search?term={name}'))
        first_result = page_content[0]['players'][0]
        if not first_result:
            raise Exception(f'Player {name} not found')
        return await get_player(config)({'id': first_result['id']})
    return inner
