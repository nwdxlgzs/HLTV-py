from enum import Enum


class MatchFormat(Enum):
    BO1 = 'bo1'
    BO3 = 'bo3'
    BO5 = 'bo5'
    BO7 = 'bo7'
    Unknown = 'unknown'


class MatchFormatLocation(Enum):
    LAN = 'LAN'
    Online = 'Online'


def from_full_match_format(format_str: str) -> MatchFormat:
    """从完整格式文本（如 'Best of 3 (Online)'）提取 MatchFormat。"""
    if 'Best of 1' in format_str:
        return MatchFormat.BO1
    if 'Best of 3' in format_str:
        return MatchFormat.BO3
    if 'Best of 5' in format_str:
        return MatchFormat.BO5
    if 'Best of 7' in format_str:
        return MatchFormat.BO7
    return MatchFormat.Unknown
