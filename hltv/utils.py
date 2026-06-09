import uuid
import asyncio
from typing import Optional, Callable, Awaitable
from bs4 import BeautifulSoup

# --- 页面抓取与验证 ---


async def fetch_page(url: str, load_page: Callable[[str], Awaitable[str]]) -> BeautifulSoup:
    """加载页面并检查 Cloudflare 拦截，返回 BeautifulSoup 对象。"""
    html = await load_page(url)
    # 检测 Cloudflare 拦截特征
    if any(x in html for x in [
        'error code:',
        'Sorry, you have been blocked',
        'Checking your browser before accessing',
        'Enable JavaScript and cookies to continue'
    ]):
        raise Exception(
            'Access denied | www.hltv.org used Cloudflare to restrict access')
    return BeautifulSoup(html, 'html.parser')


def generate_random_suffix() -> str:
    """生成随机 UUID 作为 URL 后缀，用于绕过缓存。"""
    return str(uuid.uuid4())

# --- 数值处理 ---


def parse_number(s: Optional[str]) -> Optional[int]:
    """尝试将字符串解析为整数或浮点数，失败则返回 None。"""
    if s is None:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def percentage_to_decimal_odd(odd: float) -> float:
    """将百分比赔率转换为小数赔率。"""
    return round((1 / odd) * 100, 2)

# --- ID 提取 ---


def get_id_at(index: int, href: str) -> Optional[int]:
    """从形如 '/player/1234/...' 的 href 中提取指定位置数值。"""
    parts = href.split('/')
    if index < len(parts):
        return parse_number(parts[index])
    return None

# --- 辅助 ---


def not_null(x):
    """判断对象不为 None。"""
    return x is not None


async def sleep(ms: int) -> None:
    """异步等待指定毫秒。"""
    await asyncio.sleep(ms / 1000)
