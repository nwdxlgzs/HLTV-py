from typing import Callable, Awaitable, Optional

LoadPageFunc = Callable[[str], Awaitable[str]]

class HLTVConfig:
    def __init__(self, load_page: Optional[LoadPageFunc] = None):
        if load_page is None:
            self.load_page = self._default_load_page
        else:
            self.load_page = load_page

    async def _default_load_page(self, url: str) -> str:
        try:
            from curl_cffi import requests
        except ImportError:
            raise ImportError("请安装 curl_cffi：pip install curl_cffi")
        
        # 更真实的请求头（包含 Referer 等）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.hltv.org/",
        }
        # 使用 AsyncSession，设置 impersonate 为最新的 Chrome 版本
        async with requests.AsyncSession() as session:
            resp = await session.get(
                url,
                headers=headers,
                impersonate="chrome131",  # 或尝试 "chrome124", "chrome120"
                timeout=30
            )
            resp.raise_for_status()
            return resp.text