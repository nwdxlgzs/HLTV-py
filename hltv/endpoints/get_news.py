from dataclasses import dataclass
from typing import List, Optional, Callable, Awaitable
from urllib.parse import urlencode
from ..config import HLTVConfig
from ..shared.country import Country
from ..utils import fetch_page
from ..scraper import HLTVScraper
from datetime import datetime


@dataclass
class NewsPreview:
    title: str
    comments: int
    date: int  # timestamp
    country: Country
    link: str


@dataclass
class GetNewsArguments:
    year: Optional[int] = None
    month: Optional[str] = None
    eventIds: Optional[List[int]] = None


def get_news(config: HLTVConfig) -> Callable[[Optional[GetNewsArguments]], Awaitable[List[NewsPreview]]]:
    async def inner(args: Optional[GetNewsArguments] = None) -> List[NewsPreview]:
        args = args or GetNewsArguments()
        url = 'https://www.hltv.org/news/archive'
        if args.eventIds:
            url += '?' + urlencode({'event': args.eventIds}, doseq=True)
        elif args.year and args.month:
            url += f'/{args.year}/{args.month}'

        soup = await fetch_page(url, config.load_page)
        hs = HLTVScraper(soup)

        news_list = []
        for el in hs('.article').to_array():
            link = el.attr('href')
            title = el.find('.newstext').text()
            comments_text = el.find('.newstc').children().last().text()
            comments = int(comments_text) if comments_text else 0
            date_str = el.find('.newsrecent').text()
            try:
                date_ts = int(datetime.strptime(
                    date_str, '%Y-%m-%d %H:%M').timestamp() * 1000)
            except:
                date_ts = 0
            country = Country(
                name=el.find('.newsflag').attr('alt') or '',
                code=el.find('.newsflag').attr_then(
                    'src', lambda x: x.split('/')[-1].split('.')[0]) or ''
            )
            news_list.append(NewsPreview(
                title=title,
                comments=comments,
                date=date_ts,
                country=country,
                link=link
            ))
        return news_list
    return inner
