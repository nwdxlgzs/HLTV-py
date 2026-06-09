from dataclasses import dataclass
from typing import List, Optional, Callable, Awaitable
from ..config import HLTVConfig
from ..shared.team import Team
from ..utils import fetch_page, get_id_at
from ..scraper import HLTVScraper


@dataclass
class TeamRanking:
    team: Team
    points: int
    place: int
    change: int
    isNew: bool


@dataclass
class GetTeamRankingArguments:
    year: Optional[int] = None
    month: Optional[str] = None
    day: Optional[int] = None
    country: Optional[str] = None


def get_team_ranking(config: HLTVConfig) -> Callable[[Optional[GetTeamRankingArguments]], Awaitable[List[TeamRanking]]]:
    async def inner(args: Optional[GetTeamRankingArguments] = None) -> List[TeamRanking]:
        args = args or GetTeamRankingArguments()
        year = args.year or ''
        month = args.month or ''
        day = args.day or ''
        url = f'https://www.hltv.org/ranking/teams/{year}/{month}/{day}'.replace(
            '//', '/').rstrip('/')

        soup = await fetch_page(url, config.load_page)
        hs = HLTVScraper(soup)

        if args.country:
            redirected_link = hs('.ranking-country > a').first().attr('href')
            parts = redirected_link.split('/')
            country_url = '/'.join(parts[:-1]) + '/' + args.country
            soup = await fetch_page(f'https://www.hltv.org/{country_url}', config.load_page)
            hs = HLTVScraper(soup)

        rankings = []
        for el in hs('.ranked-team').to_array():
            points = int(el.find('.points').text().replace(
                '(', '').replace(')', '').split(' ')[0])
            place = int(el.find('.position').text().lstrip('#'))
            team_name = el.find('.name').text()
            team_id = el.find('.moreLink').attr_then(
                'href', lambda h: get_id_at(2, h))
            change_text = el.find('.change').text()
            is_new = change_text == 'NEW TEAM'
            change = 0 if is_new or change_text == '-' else int(change_text)
            rankings.append(TeamRanking(
                team=Team(name=team_name, id=team_id),
                points=points,
                place=place,
                change=change,
                isNew=is_new
            ))
        return rankings
    return inner
