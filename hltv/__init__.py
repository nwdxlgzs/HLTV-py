from .config import HLTVConfig
from .endpoints.get_match import get_match, MatchStatus
from .endpoints.get_matches import get_matches, MatchEventType, MatchFilter
from .endpoints.get_recent_threads import get_recent_threads, ThreadCategory
from .endpoints.get_streams import get_streams, StreamCategory
from .endpoints.get_team import get_team, TeamPlayerType
from .endpoints.get_team_by_name import get_team_by_name
from .endpoints.get_team_ranking import get_team_ranking
from .endpoints.get_player import get_player
from .endpoints.get_player_by_name import get_player_by_name
from .endpoints.get_news import get_news
from .endpoints.get_event import get_event
from .endpoints.get_event_by_name import get_event_by_name
from .endpoints.get_events import get_events
from .endpoints.get_past_events import get_past_events
from .endpoints.get_match_stats import get_match_stats
from .endpoints.get_match_map_stats import get_match_map_stats
from .endpoints.get_matches_stats import get_matches_stats
from .endpoints.get_player_stats import get_player_stats
from .endpoints.get_player_ranking import get_player_ranking
from .endpoints.get_team_stats import get_team_stats
from .endpoints.get_results import get_results
from .endpoints.connect_to_scorebot import connect_to_scorebot

# 共享类型
from .shared.article import Article
from .shared.best_of_filter import BestOfFilter
from .shared.country import Country
from .shared.event import Event
from .shared.event_type import EventType
from .shared.game_map import GameMap
from .shared.match_format import MatchFormat, MatchFormatLocation
from .shared.match_type import MatchType
from .shared.player import Player
from .shared.ranking_filter import RankingFilter
from .shared.team import Team

class HLTV:
    """非官方 HLTV API 客户端"""
    def __init__(self, config: HLTVConfig = None):
        if config is None:
            config = HLTVConfig()
        self.config = config

        self.get_match = get_match(self.config)
        self.get_matches = get_matches(self.config)
        self.get_recent_threads = get_recent_threads(self.config)
        self.get_streams = get_streams(self.config)
        self.get_team = get_team(self.config)
        self.get_team_by_name = get_team_by_name(self.config)
        self.get_team_ranking = get_team_ranking(self.config)
        self.get_team_stats = get_team_stats(self.config)
        self.get_player = get_player(self.config)
        self.get_player_by_name = get_player_by_name(self.config)
        self.get_player_stats = get_player_stats(self.config)
        self.get_player_ranking = get_player_ranking(self.config)
        self.get_news = get_news(self.config)
        self.get_event = get_event(self.config)
        self.get_event_by_name = get_event_by_name(self.config)
        self.get_events = get_events(self.config)
        self.get_past_events = get_past_events(self.config)
        self.get_match_stats = get_match_stats(self.config)
        self.get_match_map_stats = get_match_map_stats(self.config)
        self.get_matches_stats = get_matches_stats(self.config)
        self.get_results = get_results(self.config)
        self.connect_to_scorebot = connect_to_scorebot(self.config)

    TEAM_PLACEHOLDER_IMAGE = 'https://www.hltv.org/img/static/team/placeholder.svg'
    PLAYER_PLACEHOLDER_IMAGE = 'https://static.hltv.org/images/playerprofile/bodyshot/unknown.png'

# 导出所有外部可用的类/枚举/类型，与原 index.ts 对齐
__all__ = [
    'HLTV',
    'HLTVConfig',
    # 端点常量和类型
    'MatchStatus', 'MatchEventType', 'MatchFilter', 'ThreadCategory', 'StreamCategory', 'TeamPlayerType',
    # 共享类型
    'Article', 'BestOfFilter', 'Country', 'Event', 'EventType', 'GameMap',
    'MatchFormat', 'MatchFormatLocation', 'MatchType', 'Player', 'RankingFilter', 'Team',
]