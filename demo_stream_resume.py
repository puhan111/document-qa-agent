# demo_stream_resume.py
"""验收：流式输出读到一半断开，带 Last-Event-ID 重连，断点续传不丢、不重。"""
import asyncio
import httpx

BASE = "http://localhost:8000/chat/stream"
QUESTION = "退货政策是什么"
THREAD = "demo_resume"


async def read_events(client, headers=None, stop_after=None):
    ids, datas, ev_name = [], [], None
    async with client.stream(
        "GET", BASE, params={"question": QUESTION, "thread_id": THREAD}, headers=headers or {}
    ) as r:
        async for line in r.aiter_lines():
            if line.startswith("id:"):
                ids.append(int(line.split(":", 1)[1].strip()))
            elif line.startswith("event:"):
                ev_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                datas.append(line.split(":", 1)[1].strip())
            if stop_after and len(ids) >= stop_after:
                break
    return ids, "".join(datas), ev_name


async def main():
    async with httpx.AsyncClient(timeout=None) as client:
        ids1, _, _ = await read_events(client, headers={}, stop_after=5)
        last = ids1[-1]
        print(f"第一次读到 {len(ids1)} 个事件，最后一个 id={last}，主动断开")

        ids2, content2, _ = await read_events(
            client, headers={"Last-Event-ID": str(last)}, stop_after=None
        )
        print(f"重连后读到 {len(ids2)} 个事件，拼接内容：{content2[:60]}...")

        all_ids = ids1 + ids2
        if len(all_ids) == len(set(all_ids)):
            print("✅ 无重复事件")
        else:
            print("❌ 有重复事件")
        if ids2 and ids2[0] > last:
            print("✅ 续传正确（从断点之后开始）")
        else:
            print("❌ 续传异常")


asyncio.run(main())