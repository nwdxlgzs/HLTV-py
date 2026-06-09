from dataclasses import dataclass
from typing import Optional


@dataclass
class Event:
    name: str
    id: Optional[int] = None
