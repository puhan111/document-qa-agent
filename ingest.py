import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

from parse import parse_file

load_dotenv()


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
    """把一段文字转成一个向量（一串数字）"""
    resp = embedding_client.embeddings.create(
        model=os.getenv("EMBEDDING_MODEL"),
        input=text,
    )
    return resp.data[0].embedding


def ingest_file(path, collection_name="docs"):
    """把文件解析 → 分块 → 向量化 → 存进 Chroma，返回存了多少块"""
    text = parse_file(path)                        # 1. 解析成文字
    chunks = chunk_text(text)                      # 2. 分块
    embeddings = [embed_text(c) for c in chunks]   # 3. 每块转成向量

    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name=collection_name)

    ids = [f"{path}:{i}" for i in range(len(chunks))]
    collection.upsert(
        ids=ids,
        documents=chunks,        # 原文：检索到后给模型看
        embeddings=embeddings,   # 向量：用来算相似度
        metadatas=[{"source": path} for _ in chunks],  # 来源：后面引用溯源用
    )
    return len(chunks)


if __name__ == "__main__":
    n = ingest_file("test.docx")
    print(f"已入库 {n} 块")