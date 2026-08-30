# steam_store.py
"""SSE 事件缓冲：按 stream_id 缓存已发送的事件，支持 Last-Event-ID 断点续传。

说明：进程内全局单例即可（单 worker 部署）；多 worker 需换 Redis。
"""
import time
from collections import OrderedDict
from threading import Lock
from typing import List


class StreamStore:
    def __init__(self, capacity=2000, ttl=600):
        self.capacity = capacity
        self.ttl = ttl
        self._next_id = 0             # 全局自增事件 id
        self._events = OrderedDict()  # stream_id -> list of event dicts
        self._lock = Lock()

    def create(self, stream_id: str) -> None:
        with self._lock:
            self._events[stream_id] = []

    def append(self, stream_id: str, event: str, data: str) -> int:
        with self._lock:
            self._next_id += 1
            eid = self._next_id
            self._events.setdefault(stream_id, []).append(
                {"id": eid, "event": event, "data": data, "ts": time.time()}
            )
            lst = self._events[stream_id]
            if len(lst) > self.capacity:            # 超容量丢最旧
                lst[: len(lst) - self.capacity] = []
        return eid

    def get_events(self, stream_id: str, last_id: int = 0) -> List[dict]:
        with self._lock:
            return [e for e in self._events.get(stream_id, []) if e["id"] > last_id]

    def has_id(self, stream_id: str, last_id: int) -> bool:
        with self._lock:
            lst = self._events.get(stream_id, [])
            if not lst:
                return False
            return lst[0]["id"] <= last_id   # 缓冲起点 ≤ last_id，说明 last_id 那部分还在

    def cleanup(self):
        now = time.time()
        with self._lock:
            for sid in list(self._events.keys()):
                lst = self._events[sid]
                while lst and now - lst[0]["ts"] > self.ttl:
                    lst.pop(0)
                if not lst:
                    del self._events[sid]


_store = StreamStore()