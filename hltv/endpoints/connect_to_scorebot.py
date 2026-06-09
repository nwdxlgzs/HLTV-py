import asyncio
from typing import Callable, Awaitable, Optional, Any, Dict
from ..config import HLTVConfig
from ..utils import fetch_page, generate_random_suffix
from ..scraper import HLTVScraper

# 注意：需要安装 python-socketio[client] 版本与 socket.io v2 兼容
# 原项目使用 socket.io-client 2.4.0，因此这里尝试使用 v2 客户端
# 如果无法安装 v2 客户端，可改用 socketIO-client-2 (socketio_v2)
try:
    import socketio
except ImportError:
    raise ImportError(
        "Please install python-socketio[client]: pip install python-socketio[client]")

# 以下数据结构保持与 TypeScript 版本一致，可按需定义 dataclass
# 这里提供类型提示，不强制定义 dataclass 以简化

ConnectToScorebotParams = Dict[str, Any]  # 实际包含回调函数


def connect_to_scorebot(config: HLTVConfig) -> Callable:
    """返回一个函数，该函数接受参数并启动 Scorebot 连接。
       注意：这个函数会立即创建异步任务，不会阻塞。
    """
    def inner(params: dict):
        """
        参数:
            id: int (比赛ID)
            onScoreboardUpdate: (data: dict, done: callable) -> None
            onLogUpdate: (data: dict, done: callable) -> None
            onFullLogUpdate: (data: dict, done: callable) -> None
            onConnect: () -> None
            onDisconnect: () -> None
        """
        async def run():
            match_id = params['id']
            on_scoreboard_update = params.get('onScoreboardUpdate')
            on_log_update = params.get('onLogUpdate')
            on_full_log_update = params.get('onFullLogUpdate')
            on_connect = params.get('onConnect')
            on_disconnect = params.get('onDisconnect')

            # 获取页面解析 scorebot URL 和 ID
            soup = await fetch_page(
                f'https://www.hltv.org/matches/{match_id}/{generate_random_suffix()}',
                config.load_page
            )
            hs = HLTVScraper(soup)
            scorebot_url_attr = hs('#scoreboardElement').attr(
                'data-scorebot-url')
            if not scorebot_url_attr:
                raise Exception('Scorebot URL not found')
            url = scorebot_url_attr.split(',').pop()
            match_id_str = hs('#scoreboardElement').attr('data-scorebot-id')

            # 创建 socket.io 客户端（v2 兼容模式）
            sio = socketio.Client()
            reconnected = False

            @sio.on('connect')
            def handle_connect():
                nonlocal reconnected
                def done(): return sio.disconnect()
                if on_connect:
                    on_connect()
                if not reconnected:
                    sio.emit('readyForMatch', {
                             'token': '', 'listId': match_id_str})

                @sio.on('scoreboard')
                def on_scoreboard(data):
                    if on_scoreboard_update:
                        on_scoreboard_update(data, done)

                @sio.on('log')
                def on_log(data):
                    if on_log_update:
                        # 原版需要 JSON.parse
                        if isinstance(data, str):
                            try:
                                parsed = __import__('json').loads(data)
                            except:
                                parsed = data
                        else:
                            parsed = data
                        on_log_update(parsed, done)

                @sio.on('fullLog')
                def on_full_log(data):
                    if on_full_log_update:
                        if isinstance(data, str):
                            try:
                                parsed = __import__('json').loads(data)
                            except:
                                parsed = data
                        else:
                            parsed = data
                        on_full_log_update(parsed, done)

            @sio.on('reconnect')
            def handle_reconnect():
                nonlocal reconnected
                reconnected = True
                sio.emit('readyForMatch', {
                         'token': '', 'listId': match_id_str})

            @sio.on('disconnect')
            def handle_disconnect():
                if on_disconnect:
                    on_disconnect()

            # 连接到服务器
            await sio.connect(url, transports=['websocket'])

        # 启动异步任务，不阻塞调用者
        asyncio.create_task(run())

    return inner
