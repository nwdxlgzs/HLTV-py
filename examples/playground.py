"""
使用示例：测试 HLTV API 各项功能。
根据原项目 src/playground.ts 翻译。
"""
import asyncio
from hltv import HLTV


async def main():
    hltv = HLTV()

    # 取消注释以测试对应端点
    match = await hltv.get_match({'id': 2346924})
    print(match)

    matches = await hltv.get_matches()
    print(matches)

    threads = await hltv.get_recent_threads()
    print(threads)

    streams = await hltv.get_streams()
    print(streams)

    team = await hltv.get_team({'id': 7020})
    print(team)

    player = await hltv.get_player({'id': 7998})
    print(player)

    events = await hltv.get_events()
    print(events)

    print("HLTV Python API is ready. Uncomment endpoints above to test.")

if __name__ == "__main__":
    asyncio.run(main())
