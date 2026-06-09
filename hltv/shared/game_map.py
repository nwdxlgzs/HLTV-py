from enum import Enum
from typing import Optional


class GameMap(Enum):
    TBA = 'tba'
    Train = 'de_train'
    Cobblestone = 'de_cbble'
    Inferno = 'de_inferno'
    Cache = 'de_cache'
    Mirage = 'de_mirage'
    Overpass = 'de_overpass'
    Dust2 = 'de_dust2'
    Nuke = 'de_nuke'
    Tuscan = 'de_tuscan'
    Vertigo = 'de_vertigo'
    Season = 'de_season'
    Ancient = 'de_ancient'
    Anubis = 'de_anubis'
    Default = 'default'


def from_map_slug(slug: str) -> GameMap:
    """将比赛统计表格中的地图缩写转换为 GameMap 枚举。"""
    mapping = {
        'tba': GameMap.TBA,
        'trn': GameMap.Train,
        'cbl': GameMap.Cobblestone,
        'inf': GameMap.Inferno,
        'cch': GameMap.Cache,
        'mrg': GameMap.Mirage,
        'ovp': GameMap.Overpass,
        'd2': GameMap.Dust2,
        'nuke': GameMap.Nuke,
        'tcn': GameMap.Tuscan,
        'vtg': GameMap.Vertigo,
        'anc': GameMap.Ancient,
        '-': GameMap.Default,
    }
    return mapping.get(slug, GameMap.Default)


def from_map_name(name: str) -> GameMap:
    """将完整地图名称转换为 GameMap 枚举。"""
    mapping = {
        'TBA': GameMap.TBA,
        'Train': GameMap.Train,
        'Train_se': GameMap.Train,
        'Cobblestone': GameMap.Cobblestone,
        'Inferno': GameMap.Inferno,
        'Inferno_se': GameMap.Inferno,
        'Cache': GameMap.Cache,
        'Mirage': GameMap.Mirage,
        'Mirage_ce': GameMap.Mirage,
        'Overpass': GameMap.Overpass,
        'Dust2': GameMap.Dust2,
        'Dust2_se': GameMap.Dust2,
        'Nuke': GameMap.Nuke,
        'Nuke_se': GameMap.Nuke,
        'Tuscan': GameMap.Tuscan,
        'Vertigo': GameMap.Vertigo,
        'Ancient': GameMap.Ancient,
        'Anubis': GameMap.Anubis,
        'Default': GameMap.Default,
    }
    return mapping.get(name, GameMap.Default)


def to_map_filter(game_map: GameMap) -> str:
    """将 GameMap 枚举转换为 API 过滤参数值。"""
    filters = {
        GameMap.Cache: 'de_cache',
        GameMap.Cobblestone: 'de_cobblestone',
        GameMap.Overpass: 'de_overpass',
        GameMap.Dust2: 'de_dust2',
        GameMap.Inferno: 'de_inferno',
        GameMap.Mirage: 'de_mirage',
        GameMap.Nuke: 'de_nuke',
        GameMap.Train: 'de_train',
        GameMap.Tuscan: 'de_tuscan',
        GameMap.Vertigo: 'de_vertigo',
        GameMap.Ancient: 'de_ancient',
        GameMap.Anubis: 'de_anubis',
        GameMap.Season: 'de_season',
    }
    if game_map in (GameMap.TBA, GameMap.Default):
        raise ValueError(f"Invalid map filter - {game_map}")
    return filters.get(game_map, '')
