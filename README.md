# 企业文档知识库问答 Agent

> 上传 PDF / Word 文档 → 自动解析 → 建立知识库 → 智能问答，回答时给出处，避免模型乱编。

## 一句话介绍

一个基于 RAG + LangGraph 的文档问答系统：企业把 PDF / Word 资料丢进来，就能得到一个"懂这些资料"的 AI 问答助手，回答会标注引用来源（`[1]`），保证可追溯、减少幻觉。

## 功能特性

- 文档上传：支持 PDF、Word
- 文档解析：PyMuPDF（PDF）+ python-docx（Word）
- 知识库构建：分块 + 向量化 + Chroma 入库
- 智能问答：LangGraph Agent + RAG 检索，带引用溯源
- 多轮对话：checkpointer + thread_id 记忆上下文
- 防幻觉：Prompt 约束 + 低 temperature + 引用溯源
- 服务化：FastAPI 提供 REST 接口 + 自动 Swagger 文档
- 容器化：Docker 一键部署

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI + Uvicorn |
| Agent 编排 | LangGraph |
| 文档解析 | PyMuPDF、python-docx |
| 向量库 | Chroma |
| Embedding | 通义 text-embedding |
| 大模型 | DeepSeek |
| 部署 | Docker |

## 架构

```mermaid
flowchart TB
    subgraph 入库["文档入库"]
        A[上传 PDF/Word] --> B[parse.py 解析为文本]
        B --> C[ingest.py 分块 + 向量化]
        C --> D[(Chroma 向量库)]
    end
    subgraph 问答["智能问答"]
        E[用户提问] --> F[server.py /chat]
        F --> G[agent.py LangGraph]
        G --> H[search_docs 检索]
        H --> D
        G --> I[带 [1] 引用的回答]
    end
```

## 项目结构

```
docqa/
├── parse.py             # 文档解析：PDF/Word → 纯文本
├── ingest.py            # 知识库构建：分块 + 向量化 + Chroma 入库
├── agent.py             # LangGraph 问答 Agent（RAG 检索 + 引用 + 防幻觉 + 多轮记忆）
├── server.py            # FastAPI 服务（/health /chat /upload）
├── make_test_files.py   # 生成测试文档
├── requirements.txt     # 依赖
├── Dockerfile           # 容器化
├── .dockerignore
├── .env.example         # 环境变量模板
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置密钥

```bash
cp .env.example .env
# 编辑 .env，填入 LLM（DeepSeek）和 Embedding（通义）的 key
# 具体变量名以你的 .env.example 为准
```

### 3. 建知识库

```bash
python ingest.py          # 把文档分块、向量化、存入 Chroma
```

### 4. 启动服务

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

访问 Swagger 文档：http://localhost:8000/docs

### 5. 调用接口

```bash
# 上传文档
curl -X POST http://localhost:8000/upload -F "file=@test.pdf"

# 提问
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"退货政策是什么"}'
```

## 接口说明

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 健康检查 |
| POST | /upload | 上传 PDF/Word，解析并入库 |
| POST | /chat | 问答，请求体 {question, thread_id} |

## 核心数据流

**入库**：上传文件 → `parse_file` 按后缀分流（docx→python-docx，pdf→PyMuPDF）→ `chunk_text` 分块 → `embed_text` 向量化 → 存入 Chroma（原文 + 向量 + 来源）。

**问答**：`POST /chat` → LangGraph Agent → 模型判断要不要检索 → `search_docs`（问题向量化 → Chroma 查 top3）→ 模型基于资料生成带 `[1]` 引用的回答。

## 技术选型理由

| 选择 | 为什么 |
|---|---|
| LangGraph | 用图 + 状态清晰表达 Agent 循环，自带 checkpointer 做多轮记忆 |
| Chroma | 轻量、本地可跑，适合中小项目；生产可换 Milvus / Elasticsearch |
| FastAPI | 自动校验 + 自动 Swagger 文档，适合把 Agent 包成服务 |
| DeepSeek | 云 API 免部署、成本低 |
| Docker | 一次打包、到处运行，部署一致 |

## Docker 部署

```bash
docker build -t docqa .
docker run -d --name docqa -p 8000:8000 --env-file .env docqa
```

## 已知局限（后续计划）

- 检索目前是单一向量 top3，未加混合检索与重排序
- 记忆用 InMemorySaver（内存版），重启丢失，生产需换持久化
- 未做用户认证与多用户文档隔离
