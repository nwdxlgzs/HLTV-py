from typing import Callable, Awaitable
from ..config import HLTVConfig
from .get_team import FullTeam, get_team


def get_team_by_name(config: HLTVConfig) -> Callable[[dict], Awaitable[FullTeam]]:
    async def inner(params: dict) -> FullTeam:
        name = params['name']
        import json
        page_content = json.loads(await config.load_page(f'https://www.hltv.org/search?term={name}'))
        first_result = page_content[0]['teams'][0]
        if not first_result:
            raise Exception(f'Team {name} not found')
        return await get_team(config)({'id': first_result['id']})
    return inner
