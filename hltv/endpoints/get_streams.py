from dataclasses import dataclass
from enum import Enum
from typing import List, Callable, Awaitable
from ..config import HLTVConfig
from ..shared.country import Country
from ..utils import fetch_page, parse_number
from ..scraper import HLTVScraper
import time


class StreamCategory(Enum):
    TopPlayer = 'Top player'
    Caster = 'Caster'
    FemalePlayer = 'Female Player'
    Organizer = 'Organizer'          # 新增：主办方


@dataclass
class FullStream:
    name: str
    category: StreamCategory
    country: Country
    link: str
    viewers: int


def get_streams(config: HLTVConfig) -> Callable[[], Awaitable[List[FullStream]]]:
    async def inner() -> List[FullStream]:
        url = f'https://www.hltv.org/?_={int(time.time() * 1000)}'
        soup = await fetch_page(url, config.load_page)
        hs = HLTVScraper(soup)

        streams = []
        for el in hs('.streams-stream').to_array():
            name = el.find('.streams-name').text()
            cat_title = el.find('.streams-category').attr('title')
            # 容错：无法识别的类别跳过
            if not cat_title:
                continue
            try:
                category = StreamCategory(cat_title)
            except ValueError:
                continue

            country = Country(
                name=el.find('.streams-flag').attr('title'),
                code=el.find('.streams-flag').attr_then(
                    'src',
                    lambda x: x.split('/')[-1].split('.')[0]
                ) or ''
            )
            viewers_str = el.find('.streams-viewers').text()
            viewers = parse_number(viewers_str.replace(
                '(', '').replace(')', '')) or 0
            link = el.data('frontpage-stream-embed-src')
            streams.append(FullStream(
                name=name,
                category=category,
                country=country,
                link=link,
                viewers=viewers
            ))
        return streams
    return inner
