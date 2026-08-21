import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from agent import ask
from ingest import ingest_file

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


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    dest = UPLOAD_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    n = ingest_file(str(dest))
    return {"filename": file.filename, "chunks": n}