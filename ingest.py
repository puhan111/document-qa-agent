# -*- coding: utf-8 -*-
"""入库：分块 + 向量化 + 存 Chroma（支持流式分批，避免大文件一次读入内存）。"""
import os
import logging

from dotenv import load_dotenv
from openai import OpenAI
import chromadb

from parse import parse_file, parse_file_stream

load_dotenv()

logger = logging.getLogger(__name__)

CHUNK_BATCH = 32


def chunk_text(text, chunk_size=500, chunk_overlap=50):
    """把长文本切成小块，块与块之间有重叠，避免切断上下文。"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += chunk_size - chunk_overlap
    return chunks


embedding_client = OpenAI(
    api_key=os.getenv("EMBEDDING_API_KEY"),
    base_url=os.getenv("EMBEDDING_BASE_URL"),
)


def embed_text(text):
    """把一段文字转成一个向量（一串数字）。"""
    resp = embedding_client.embeddings.create(
        model=os.getenv("EMBEDDING_MODEL"),
        input=text,
    )
    return resp.data[0].embedding


def ingest_file_stream(path, collection_name="docs", batch_size=CHUNK_BATCH):
    """流式入库：逐段解析 → 分块 → 分批向量化 + upsert。返回存了多少块。"""
    # 先数一遍总共多少块，用于进度显示
    total = sum(len(chunk_text(part)) for part in parse_file_stream(path))

    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name=collection_name)

    done = 0
    batch_ids, batch_docs, batch_vec, batch_meta = [], [], [], []

    for part in parse_file_stream(path):
        for c in chunk_text(part):
            batch_ids.append(f"{path}:{done}")
            batch_docs.append(c)
            batch_vec.append(embed_text(c))
            batch_meta.append({"source": path})
            done += 1
            if len(batch_docs) >= batch_size:
                collection.upsert(
                    ids=batch_ids, documents=batch_docs,
                    embeddings=batch_vec, metadatas=batch_meta,
                )
                logger.info("已入库 %d/%d 块", done, total)
                batch_ids, batch_docs, batch_vec, batch_meta = [], [], [], []

    if batch_docs:
        collection.upsert(
            ids=batch_ids, documents=batch_docs,
            embeddings=batch_vec, metadatas=batch_meta,
        )
        logger.info("已入库 %d/%d 块", done, total)

    return done


def ingest_file(path, collection_name="docs"):
    """把文件解析 → 分块 → 向量化 → 存进 Chroma，返回存了多少块。"""
    return ingest_file_stream(path, collection_name)


if __name__ == "__main__":
    n = ingest_file("test.docx")
    print(f"已入库 {n} 块")