from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    name: str
    id: Optional[int] = None
