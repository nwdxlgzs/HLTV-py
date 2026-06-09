> [!WARNING]  
> This library is no longer actively maintained. | 本库已停止主动维护。

<h1 align="center">
  <img src="https://www.hltv.org/img/static/TopLogo2x.png" alt="HLTV logo" width="200">
  <br>
  The unofficial HLTV Node.js API → Python port
  <br>
  <small>非官方 HLTV API · Python 版</small>
</h1>

## Table of contents · 目录

- [Table of contents · 目录](#table-of-contents--目录)
- [Installation · 安装](#installation--安装)
- [Usage · 用法](#usage--用法)
  - [Custom configuration · 自定义配置](#custom-configuration--自定义配置)
- [API · 接口](#api--接口)
  - [getMatch](#getmatch)
  - [getMatches](#getmatches)
  - [getMatchesStats](#getmatchesstats)
  - [getMatchStats](#getmatchstats)
  - [getMatchMapStats](#getmatchmapstats)
  - [getStreams](#getstreams)
  - [getRecentThreads](#getrecentthreads)
  - [getTeamRanking](#getteamranking)
  - [getTeam](#getteam)
  - [getTeamByName](#getteambyname)
  - [getTeamStats](#getteamstats)
  - [getPlayer](#getplayer)
  - [getPlayerByName](#getplayerbyname)
  - [getPlayerStats](#getplayerstats)
  - [getPlayerRanking](#getplayerranking)
  - [getEvents](#getevents)
  - [getEvent](#getevent)
  - [getEventByName](#geteventbyname)
  - [getPastEvents](#getpastevents)
  - [getResults](#getresults)
  - [getNews](#getnews)
  - [connectToScorebot](#connecttoscorebot)
- [Constants · 常量](#constants--常量)
- [License · 许可证](#license--许可证)

---

## Installation · 安装

```bash
pip install hltv-py
# or from source
pip install .
```

**Dependencies · 依赖**：
- `httpx` – 异步 HTTP 请求 (replaces `got-scraping`)
- `beautifulsoup4` – HTML 解析 (replaces `cheerio`)
- `python-socketio[client]` – 实时比分 WebSocket (replaces `socket.io-client@2.4`)

---

## Usage · 用法

⚠️ **WARNING · 警告：** Abusing this library will likely result in an IP ban from HLTV simply because of Cloudflare bot protection.  
滥用本库极可能导致 HLTV 通过 Cloudflare 封禁你的 IP。

Please use with caution and try to limit the rate and amount of your requests.  
请谨慎使用，尽量控制请求频率与数量。

All endpoints are **asynchronous** and must be `await`ed.  
所有端点均为**异步**，需要使用 `await` 调用。

```python
import asyncio
from hltv import HLTV

async def main():
    hltv = HLTV()
    match = await hltv.get_match({'id': 2306295})
    print(match)

asyncio.run(main())
```

### Custom configuration · 自定义配置

You can pass a custom `HLTVConfig` with your own `load_page` function.  
你可以传入自定义的 `HLTVConfig`，提供自己的页面加载函数。

```python
from hltv import HLTV, HLTVConfig
import httpx

async def my_load_page(url: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.text

config = HLTVConfig(load_page=my_load_page)
hltv = HLTV(config)
```

---

## API · 接口

All methods return a data object (dataclass) matching the original TypeScript schema.  
所有方法返回的数据对象（dataclass）与原 TypeScript 版本结构一致。

---

### getMatch

Fetches details of a single match. | 获取单场比赛详情。

| Option | Type   | Default | Description       |
|--------|--------|---------|-------------------|
| id     | int    | -       | The match ID      |

```python
match = await hltv.get_match({'id': 2306295})
```

---

### getMatches

Fetches list of matches from `hltv.org/matches/`. | 获取比赛列表。

| Option    | Type                | Default | Description              |
|-----------|---------------------|---------|--------------------------|
| eventIds  | list[int] or None   | None    | Filter by event IDs      |
| eventType | MatchEventType      | None    | Filter by event type     |
| filter    | MatchFilter         | None    | Pre‑set category filter  |
| teamIds   | list[int] or None   | None    | Filter by team IDs       |

```python
matches = await hltv.get_matches()
```

---

### getMatchesStats

Fetches paginated match stats. | 分页获取比赛统计数据。

| Option                  | Type         | Default | Description                            |
|-------------------------|--------------|---------|----------------------------------------|
| startDate               | str or None  | None    | e.g. `'2017-07-10'`                   |
| endDate                 | str or None  | None    |                                        |
| matchType               | MatchType    | None    |                                        |
| maps                    | list[GameMap]| None    |                                        |
| rankingFilter           | RankingFilter| None    |                                        |
| delayBetweenPageRequests| int          | 0       | Milliseconds to wait between pages     |

```python
# ⚠️ Can make many requests if results span multiple pages.
stats = await hltv.get_matches_stats({'startDate': '2017-07-10', 'endDate': '2017-07-18'})
```

---

### getMatchStats

Fetches overall match stats. | 获取整场比赛总体统计。

| Option | Type | Default | Description    |
|--------|------|---------|----------------|
| id     | int  | -       | Match stats ID |

```python
stats = await hltv.get_match_stats({'id': 62979})
```

---

### getMatchMapStats

Fetches single map stats. | 获取单张地图统计。

| Option | Type | Default | Description      |
|--------|------|---------|------------------|
| id     | int  | -       | Map stats ID     |

```python
map_stats = await hltv.get_match_map_stats({'id': 49968})
```

---

### getStreams

Fetches live streams from the front page. | 获取首页直播流。

| Option    | Type | Default | Description                          |
|-----------|------|---------|--------------------------------------|
| loadLinks | bool | False   | (Not implemented in this port yet)   |

```python
streams = await hltv.get_streams()
```

---

### getRecentThreads

Fetches latest forum threads. | 获取最新论坛帖子。

No arguments.

```python
threads = await hltv.get_recent_threads()
```

---

### getTeamRanking

Fetches team ranking. | 获取战队排名。

| Option  | Type                   | Default | Description                            |
|---------|------------------------|---------|----------------------------------------|
| year    | int or None            | None    | e.g. `2017`                           |
| month   | str or None            | None    | e.g. `'may'`                          |
| day     | int or None            | None    |                                        |
| country | str or None            | None    | Capitalized, e.g. `'Brazil'`          |

```python
ranking = await hltv.get_team_ranking({'year': 2017, 'month': 'may', 'day': 29})
```

---

### getTeam

Fetches team details. | 获取战队详情。

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| id     | int  | -       | Team ID     |

```python
team = await hltv.get_team({'id': 6137})
```

---

### getTeamByName

Same as `getTeam` but by name. | 同 `getTeam`，按名称查询。

| Option | Type | Default | Description  |
|--------|------|---------|--------------|
| name   | str  | -       | Team name    |

```python
team = await hltv.get_team_by_name({'name': 'BIG'})
```

---

### getTeamStats

Fetches team statistics. | 获取战队统计数据。

| Option           | Type         | Default | Description                   |
|------------------|--------------|---------|-------------------------------|
| id               | int          | -       | Team ID                       |
| currentRosterOnly| bool         | False   | Stats for current lineup only |
| startDate        | str or None  | None    |                               |
| endDate          | str or None  | None    |                               |
| matchType        | MatchType    | None    |                               |
| rankingFilter    | RankingFilter| None    |                               |
| maps             | list[GameMap]| None    |                               |
| bestOfX          | BestOfFilter | None    |                               |

```python
stats = await hltv.get_team_stats({'id': 6137})
```

---

### getPlayer

Fetches player profile. | 获取选手资料。

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| id     | int  | -       | Player ID   |

```python
player = await hltv.get_player({'id': 7998})
```

---

### getPlayerByName

Same as `getPlayer` but by nickname. | 同 `getPlayer`，按昵称查询。

| Option | Type | Default | Description   |
|--------|------|---------|---------------|
| name   | str  | -       | Player nickname|

```python
player = await hltv.get_player_by_name({'name': 'chrisJ'})
```

---

### getPlayerStats

Fetches detailed player statistics. | 获取选手详细数据。

| Option        | Type         | Default | Description |
|---------------|--------------|---------|-------------|
| id            | int          | -       | Player ID   |
| startDate     | str or None  | None    |             |
| endDate       | str or None  | None    |             |
| matchType     | MatchType    | None    |             |
| rankingFilter | RankingFilter| None    |             |
| maps          | list[GameMap]| None    |             |
| bestOfX       | BestOfFilter | None    |             |
| eventIds      | list[int]    | None    |             |

```python
stats = await hltv.get_player_stats({'id': 7998})
```

---

### getPlayerRanking

Fetches player ranking list. | 获取选手排行榜。

| Option        | Type              | Default | Description |
|---------------|-------------------|---------|-------------|
| startDate     | str or None       | None    |             |
| endDate       | str or None       | None    |             |
| matchType     | MatchType         | None    |             |
| rankingFilter | RankingFilter     | None    |             |
| maps          | list[GameMap]     | None    |             |
| minMapCount   | int or None       | None    |             |
| countries     | list[str] or None | None    |             |
| bestOfX       | BestOfFilter      | None    |             |

```python
ranking = await hltv.get_player_ranking({'startDate': '2018-07-01', 'endDate': '2018-10-01'})
```

---

### getEvents

Fetches upcoming/ongoing events. | 获取即将进行/进行中的赛事。

| Option            | Type         | Default | Description               |
|-------------------|--------------|---------|---------------------------|
| eventType         | EventType    | None    |                           |
| prizePoolMin      | int or None  | None    | Minimum prize pool (USD)  |
| prizePoolMax      | int or None  | None    | Maximum prize pool (USD)  |
| attendingTeamIds  | list[int]    | None    |                           |
| attendingPlayerIds| list[int]    | None    |                           |

```python
events = await hltv.get_events()
```

---

### getEvent

Fetches full event details. | 获取完整赛事详情。

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| id     | int  | -       | Event ID    |

```python
event = await hltv.get_event({'id': 3389})
```

---

### getEventByName

Same as `getEvent` but by name. | 同 `getEvent`，按名称查询。

| Option | Type | Default | Description  |
|--------|------|---------|--------------|
| name   | str  | -       | Event name   |

```python
event = await hltv.get_event_by_name({'name': 'IEM Katowice 2019'})
```

---

### getPastEvents

Fetches archived events (paginated). | 分页获取历史赛事。

| Option                  | Type         | Default | Description                        |
|-------------------------|--------------|---------|------------------------------------|
| startDate               | str or None  | None    |                                    |
| endDate                 | str or None  | None    |                                    |
| eventType               | EventType    | None    |                                    |
| prizePoolMin            | int or None  | None    |                                    |
| prizePoolMax            | int or None  | None    |                                    |
| attendingTeamIds        | list[int]    | None    |                                    |
| attendingPlayerIds      | list[int]    | None    |                                    |
| delayBetweenPageRequests| int          | 0       |                                    |

```python
past = await hltv.get_past_events({'startDate': '2019-01-01', 'endDate': '2019-01-10'})
```

---

### getResults

Fetches match results (paginated). | 分页获取比赛结果。

| Option                  | Type              | Default | Description                      |
|-------------------------|-------------------|---------|----------------------------------|
| startDate               | str or None       | None    |                                  |
| endDate                 | str or None       | None    |                                  |
| matchType               | ResultsMatchType  | None    |                                  |
| stars                   | int (1‑5) or None | None    |                                  |
| maps                    | list[GameMap]     | None    |                                  |
| countries               | list[str]         | None    |                                  |
| bestOfX                 | BestOfFilter      | None    |                                  |
| contentFilters          | list[ContentFilter]| None   |                                  |
| eventIds                | list[int]         | None    |                                  |
| playerIds               | list[int]         | None    |                                  |
| teamIds                 | list[int]         | None    |                                  |
| game                    | GameType          | None    |                                  |
| delayBetweenPageRequests| int               | 0       |                                  |

```python
results = await hltv.get_results({'eventIds': [1617]})
```

---

### getNews

Fetches news archive. | 获取新闻存档。

| Option   | Type        | Default | Description                    |
|----------|-------------|---------|--------------------------------|
| year     | int or None | None    | Must also provide month        |
| month    | str or None | None    | Must also provide year         |
| eventIds | list[int]   | None    |                                |

```python
news = await hltv.get_news({'year': 2020, 'month': 'may'})
```

---

### connectToScorebot

Real‑time match scoreboard via WebSocket. | 通过 WebSocket 获取实时比分。

| Option              | Type        | Default | Description                                |
|---------------------|-------------|---------|--------------------------------------------|
| id                  | int         | -       | Match ID                                   |
| onScoreboardUpdate  | callable    | None    | Callback when scoreboard changes           |
| onLogUpdate         | callable    | None    | Callback when new log entry arrives        |
| onFullLogUpdate     | callable    | None    |                                            |
| onConnect           | callable    | None    |                                            |
| onDisconnect        | callable    | None    |                                            |

```python
hltv.connect_to_scorebot({
    'id': 2311609,
    'onScoreboardUpdate': lambda data, done: print(data),
    'onLogUpdate': lambda data, done: print(data),
})
```
*Note: Callbacks are synchronous, but the connection runs in an async background task.*  
*注意：回调函数为同步，但连接在异步后台任务中运行。*

---

## Constants · 常量

```python
HLTV.TEAM_PLACEHOLDER_IMAGE   # 'https://www.hltv.org/img/static/team/placeholder.svg'
HLTV.PLAYER_PLACEHOLDER_IMAGE # 'https://static.hltv.org/images/playerprofile/bodyshot/unknown.png'
```

---

## License · 许可证

ISC – original library by Stanislav Iliev. Python port by contributors.  
ISC 许可证 – 原库作者 Stanislav Iliev，Python 移植由贡献者完成。
