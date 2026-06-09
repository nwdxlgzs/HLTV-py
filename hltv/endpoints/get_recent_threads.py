from dataclasses import dataclass
from enum import Enum
from typing import List, Callable, Awaitable
from ..config import HLTVConfig
from ..utils import fetch_page
from ..scraper import HLTVScraper
import time


class ThreadCategory(Enum):
    CS = 'cs'
    Match = 'match'
    News = 'news'


@dataclass
class Thread:
    title: str
    link: str
    replies: int
    category: ThreadCategory


def get_recent_threads(config: HLTVConfig) -> Callable[[], Awaitable[List[Thread]]]:
    async def inner() -> List[Thread]:
        # 使用首页 URL，附加时间戳防止缓存
        url = f'https://www.hltv.org/?_={int(time.time() * 1000)}'
        soup = await fetch_page(url, config.load_page)
        hs = HLTVScraper(soup)

        threads = []
        for el in hs('.activity').to_array():
            title = el.find('.topic').text()
            link = el.attr('href') or ''
            replies = el.contents().last().num_from_text() or 0
            category_raw = next(
                (c for c in (el.attr('class') or '').split() if c.endswith('Cat')),
                ''
            )
            category = ThreadCategory(category_raw.replace('Cat', ''))
            threads.append(Thread(title=title, link=link,
                           replies=replies, category=category))
        return threads
    return inner
