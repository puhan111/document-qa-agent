import asyncio
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import ask
from ingest import ingest_file
from stream_store import _store

app = FastAPI(title="企业文档知识库问答 Agent")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class ChatRequest(BaseModel):
    question: str
    thread_id: str = "default"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    answer = ask(req.question, req.thread_id)
    return {"answer": answer}


def _split_tokens(text: str, size: int = 2):
    """把答案切成小段，模拟逐字流式输出。"""
    return [text[i:i + size] for i in range(0, len(text), size)]


async def _emit(events):
    """按标准 SSE 格式逐条发送，每 15 秒发一次心跳。"""
    last_ping = time.monotonic()
    for e in events:
        if e.get("event") == "error":
            yield f"event: error\ndata: {e['data']}\n\n"
        else:
            yield f"id: {e['id']}\nevent: {e['event']}\ndata: {e['data']}\n\n"
        await asyncio.sleep(0.02)
        if time.monotonic() - last_ping >= 15:
            yield ": ping\n\n"
            last_ping = time.monotonic()


async def _stream(question: str, thread_id: str, request: Request):
    stream_id = f"s_{thread_id}"
    last_id = int(request.headers.get("last-event-id", "0") or "0")

    # 断线重连：从缓冲重放
    if last_id > 0:
        if _store.has_id(stream_id, last_id):
            events = _store.get_events(stream_id, last_id)
        else:
            events = [{"id": -1, "event": "error", "data": "缓冲已失效，请重新提问"}]
        return StreamingResponse(_emit(events), media_type="text/event-stream")

    # 全新生成：先算完答案（保留假流式语义），写进缓冲，再流式
    answer = ask(question, thread_id)
    _store.create(stream_id)
    for t in _split_tokens(answer):
        _store.append(stream_id, "token", t)
    _store.append(stream_id, "done", "OK")

    events = _store.get_events(stream_id, 0)
    return StreamingResponse(_emit(events), media_type="text/event-stream")


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    return await _stream(req.question, req.thread_id, request)


@app.get("/chat/stream")
async def chat_stream_get(request: Request, question: str, thread_id: str = "default"):
    return await _stream(question, thread_id, request)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    dest = UPLOAD_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    n = ingest_file(str(dest))
    return {"filename": file.filename, "chunks": n}