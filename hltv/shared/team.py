from dataclasses import dataclass
from typing import Optional


@dataclass
class Team:
    name: str
    id: Optional[int] = None
