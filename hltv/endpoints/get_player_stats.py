from dataclasses import dataclass, field
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.best_of_filter import BestOfFilter
from ..shared.country import Country
from ..shared.game_map import from_map_slug, GameMap, to_map_filter
from ..shared.match_type import MatchType
from ..shared.ranking_filter import RankingFilter
from ..shared.team import Team
from ..utils import fetch_page, generate_random_suffix, get_id_at, parse_number
from ..scraper import HLTVScraper


@dataclass
class PlayerStatsMatch:
    date: int
    team1: Team
    team2: Team
    map: GameMap
    kills: int
    deaths: int
    rating: float
    mapStatsId: int


@dataclass
class FullPlayerStats:
    id: int
    name: Optional[str] = None
    ign: str = ''
    image: Optional[str] = None
    age: Optional[int] = None
    country: Optional[Country] = None
    team: Optional[Team] = None
    matches: List[PlayerStatsMatch] = field(default_factory=list)
    overviewStatistics: dict = field(default_factory=dict)
    individualStatistics: dict = field(default_factory=dict)


@dataclass
class GetPlayerStatsArguments:
    id: int
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    matchType: Optional[MatchType] = None
    rankingFilter: Optional[RankingFilter] = None
    maps: Optional[List[GameMap]] = None
    bestOfX: Optional[BestOfFilter] = None
    eventIds: Optional[List[int]] = None


def get_player_stats(config: HLTVConfig) -> Callable[[GetPlayerStatsArguments], Awaitable[FullPlayerStats]]:
    async def inner(options: GetPlayerStatsArguments) -> FullPlayerStats:
        query = {}
        if options.startDate:
            query['startDate'] = options.startDate
        if options.endDate:
            query['endDate'] = options.endDate
        if options.matchType:
            query['matchType'] = options.matchType.value
        if options.rankingFilter:
            query['rankingFilter'] = options.rankingFilter.value
        if options.maps:
            query['maps'] = [to_map_filter(m) for m in options.maps]
        if options.bestOfX:
            query['bestOfX'] = options.bestOfX.value
        if options.eventIds:
            query['event'] = options.eventIds
        query_str = urlencode(query, doseq=True)
        pid = options.id
        rand = generate_random_suffix()

        import asyncio
        overview_soup, individual_soup, matches_soup = await asyncio.gather(
            fetch_page(
                f'https://www.hltv.org/stats/players/{pid}/{rand}?{query_str}', config.load_page),
            fetch_page(
                f'https://www.hltv.org/stats/players/individual/{pid}/{rand}?{query_str}', config.load_page),
            fetch_page(
                f'https://www.hltv.org/stats/players/matches/{pid}/{rand}?{query_str}', config.load_page)
        )
        ov = HLTVScraper(overview_soup)
        ind = HLTVScraper(individual_soup)
        mt = HLTVScraper(matches_soup)

        # 基本信息
        name_text = ov('.summaryRealname div').text()
        name = name_text if name_text != '-' else None
        ign = ov('.context-item-name').text()
        image_url = ov('.summaryBodyshot').attr(
            'src') or ov('.summarySquare').attr('src')
        if image_url and 'bodyshot/unknown.png' in image_url:
            image_url = None
        age_text = ov('.summaryPlayerAge').text()
        age = parse_number(age_text.split(' ')[0]) if age_text else None
        country = Country(
            name=ov('.summaryRealname .flag').attr('title') or '',
            code=ov('.summaryRealname .flag').attr_then(
                'src', lambda x: x.split('/')[-1].split('.')[0]) or ''
        )
        team = None
        if ov('.SummaryTeamname').text() != 'No team':
            team = Team(
                name=ov('.SummaryTeamname a').text(),
                id=ov('.SummaryTeamname a').attr_then(
                    'href', lambda h: get_id_at(3, h))
            )

        # 概览统计
        def get_overview_stat(label: str):
            row = ov('.stats-row').filter(lambda _,
                                          x: label.lower() in x.text().lower())
            if row.exists():
                span = row.find('span').eq(1)
                return float(span.text().replace('%', '')) if span.exists() else None
            return None

        overview_statistics = {
            'kills': int(get_overview_stat('Total kills') or 0),
            'headshots': get_overview_stat('Headshot %') or 0,
            'deaths': int(get_overview_stat('Total deaths') or 0),
            'kdRatio': get_overview_stat('K/D Ratio') or 0,
            'damagePerRound': get_overview_stat('Damage / Round'),
            'grenadeDamagePerRound': get_overview_stat('Grenade dmg / Round'),
            'mapsPlayed': int(get_overview_stat('Maps played') or 0),
            'roundsPlayed': int(get_overview_stat('Rounds played') or 0),
            'killsPerRound': get_overview_stat('Kills / round') or 0,
            'assistsPerRound': get_overview_stat('Assists / round') or 0,
            'deathsPerRound': get_overview_stat('Deaths / round') or 0,
            'savedByTeammatePerRound': get_overview_stat('Saved by teammate'),
            'savedTeammatesPerRound': get_overview_stat('Saved teammates'),
        }
        rating1 = get_overview_stat('Rating 1.0')
        if rating1 is not None:
            overview_statistics['rating1'] = rating1
        else:
            overview_statistics['rating2'] = get_overview_stat(
                'Rating 2.0') or 0

        # 个人详细统计
        def get_indiv_stat(label: str):
            row = ind('.stats-row').filter(lambda _,
                                           x: label.lower() in x.text().lower())
            if row.exists():
                span = row.find('span').eq(1)
                return float(span.text().replace('%', '')) if span.exists() else 0
            return 0

        individual_statistics = {
            'roundsWithKills': int(get_indiv_stat('Rounds with kills')),
            'zeroKillRounds': int(get_indiv_stat('0 kill rounds')),
            'oneKillRounds': int(get_indiv_stat('1 kill rounds')),
            'twoKillRounds': int(get_indiv_stat('2 kill rounds')),
            'threeKillRounds': int(get_indiv_stat('3 kill rounds')),
            'fourKillRounds': int(get_indiv_stat('4 kill rounds')),
            'fiveKillRounds': int(get_indiv_stat('5 kill rounds')),
            'openingKills': int(get_indiv_stat('Total opening kills')),
            'openingDeaths': int(get_indiv_stat('Total opening deaths')),
            'openingKillRatio': get_indiv_stat('Opening kill ratio'),
            'openingKillRating': get_indiv_stat('Opening kill rating'),
            'teamWinPercentAfterFirstKill': get_indiv_stat('Team win percent after first kill'),
            'firstKillInWonRounds': int(get_indiv_stat('First kill in won rounds')),
            'rifleKills': int(get_indiv_stat('Rifle kills')),
            'sniperKills': int(get_indiv_stat('Sniper kills')),
            'smgKills': int(get_indiv_stat('SMG kills')),
            'pistolKills': int(get_indiv_stat('Pistol kills')),
            'grenadeKills': int(get_indiv_stat('Grenade')),
            'otherKills': int(get_indiv_stat('Other')),
        }

        # 比赛列表
        matches = []
        for el in mt('.stats-table tbody tr').to_array():
            cells = el.find('td')
            if cells.length < 6:
                continue
            kills_deaths = cells.eq(4).text().split(' - ')
            kills = int(kills_deaths[0]) if kills_deaths else 0
            deaths = int(kills_deaths[1]) if len(kills_deaths) > 1 else 0
            map_stats_id = cells.first().find('a').attr_then(
                'href', lambda h: get_id_at(4, h)) or 0
            date = cells.first().find('.time').num_from_attr('data-unix') or 0
            team1 = Team(
                id=cells.eq(1).find(
                    '.gtSmartphone-only a').attr_then('href', lambda h: get_id_at(3, h)),
                name=cells.eq(1).find('a span').text()
            )
            team2 = Team(
                id=cells.eq(2).find(
                    '.gtSmartphone-only a').attr_then('href', lambda h: get_id_at(3, h)),
                name=cells.eq(2).find('a span').text()
            )
            map_slug = cells.eq(3).text()  # map column
            game_map = from_map_slug(map_slug)
            rating = cells.last().num_from_text() or 0.0
            matches.append(PlayerStatsMatch(
                date=date, team1=team1, team2=team2, map=game_map,
                kills=kills, deaths=deaths, rating=rating, mapStatsId=map_stats_id
            ))

        return FullPlayerStats(
            id=pid,
            name=name,
            ign=ign,
            image=image_url,
            age=age,
            country=country,
            team=team,
            overviewStatistics=overview_statistics,
            individualStatistics=individual_statistics,
            matches=matches
        )
    return inner
