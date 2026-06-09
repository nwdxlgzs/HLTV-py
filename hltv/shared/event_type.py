from enum import Enum
from typing import Optional


class EventType(Enum):
    Major = 'MAJOR'
    InternationalLAN = 'INTLLAN'
    RegionalLAN = 'REGIONALLAN'
    LocalLAN = 'LOCALLAN'
    Online = 'ONLINE'
    Other = 'OTHER'


def from_text(text: str) -> Optional[EventType]:
    """将页面上的事件类型文本转换为 EventType 枚举。"""
    mapping = {
        'Online': EventType.Online,
        'Intl. LAN': EventType.InternationalLAN,
        'Local LAN': EventType.LocalLAN,
        'Reg. LAN': EventType.RegionalLAN,
        'Major': EventType.Major,
        'Other': EventType.Other,
    }
    return mapping.get(text)
