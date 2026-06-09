from typing import List, Optional, Callable, Any
from bs4 import Tag, BeautifulSoup
from .utils import parse_number


class HLTVElement:
    """模拟 cheerio 元素的查询与取值方法。"""

    def __init__(self, elements: List[Tag]):
        self._elements = elements

    @property
    def length(self) -> int:
        return len(self._elements)

    @property
    def _first(self) -> Optional[Tag]:
        return self._elements[0] if self._elements else None

    def find(self, selector: str) -> 'HLTVElement':
        results = []
        for el in self._elements:
            results.extend(el.select(selector))
        return HLTVElement(results)

    def first(self) -> 'HLTVElement':
        return HLTVElement([self._elements[0]] if self._elements else [])

    def last(self) -> 'HLTVElement':
        return HLTVElement([self._elements[-1]] if self._elements else [])

    def eq(self, index: int) -> 'HLTVElement':
        if 0 <= index < self.length:
            return HLTVElement([self._elements[index]])
        return HLTVElement([])

    def filter(self, func: Callable[[int, 'HLTVElement'], bool]) -> 'HLTVElement':
        filtered = []
        for i, el in enumerate(self._elements):
            if func(i, HLTVElement([el])):
                filtered.append(el)
        return HLTVElement(filtered)

    def to_array(self) -> List['HLTVElement']:
        return [HLTVElement([el]) for el in self._elements]

    def attr(self, name: str) -> Optional[str]:
        val = self._first.get(name) if self._first else None
        if isinstance(val, list):
            return ' '.join(val)
        return val

    def attr_then(self, attr: str, then: Callable[[str], Any]) -> Any:
        val = self.attr(attr)
        return then(val) if val is not None else None

    def text(self) -> str:
        return ''.join(el.get_text() for el in self._elements)

    def trim_text(self) -> Optional[str]:
        t = self.text().strip()
        return t if t else None

    def num_from_attr(self, attr: str) -> Optional[int]:
        return parse_number(self.attr(attr))

    def num_from_text(self) -> Optional[int]:
        return parse_number(self.text())

    def lines(self) -> List[str]:
        return self.text().split('\n')

    def exists(self) -> bool:
        return self.length > 0

    def data(self, name: str) -> Any:
        return self.attr('data-' + name)

    def next(self, selector: Optional[str] = None) -> 'HLTVElement':
        siblings = []
        for el in self._elements:
            nxt = el.find_next_sibling(selector)
            if nxt:
                siblings.append(nxt)
        return HLTVElement(siblings)

    def prev(self, selector: Optional[str] = None) -> 'HLTVElement':
        sibs = []
        for el in self._elements:
            prev = el.find_previous_sibling(selector)
            if prev:
                sibs.append(prev)
        return HLTVElement(sibs)

    def parent(self) -> 'HLTVElement':
        parents = []
        for el in self._elements:
            p = el.parent
            if p and isinstance(p, Tag):
                parents.append(p)
        return HLTVElement(parents)

    def children(self, selector: Optional[str] = None) -> 'HLTVElement':
        kids = []
        for el in self._elements:
            if selector:
                kids.extend(el.select(f':scope > {selector}'))
            else:
                kids.extend([c for c in el.children if isinstance(c, Tag)])
        return HLTVElement(kids)

    def contents(self) -> 'HLTVElement':
        return self.children()

    def index(self) -> int:
        if not self._elements:
            return -1
        el = self._elements[0]
        parent = el.parent
        if parent:
            tags = [c for c in parent.children if isinstance(c, Tag)]
            try:
                return tags.index(el)
            except ValueError:
                return -1
        return -1

    def __iter__(self):
        return iter(self.to_array())


class HLTVPage:
    def __init__(self, soup: BeautifulSoup):
        self._soup = soup

    def __call__(self, selector: str) -> HLTVElement:
        elements = self._soup.select(selector)
        return HLTVElement(elements)


def HLTVScraper(soup: BeautifulSoup) -> HLTVPage:
    return HLTVPage(soup)
