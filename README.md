# 企业文档知识库问答 Agent

一个基于 RAG + LangGraph 的文档智能问答系统：上传 PDF / Word 文档，自动解析、建立向量知识库，让 AI 基于文档内容带出处回答问题。

## 功能特性

- 文档解析：支持 PDF（PyMuPDF）和 Word（python-docx）
- 知识库构建：分块 → 向量化（通义 text-embedding-v3）→ 存入 Chroma
- 智能问答：LangGraph Agent 调用 RAG 检索，回答附带引用出处
- 防幻觉：Prompt 约束 + 低 temperature
- 多轮记忆：checkpointer + thread_id
- 服务化：FastAPI + 自动 Swagger 文档
- 容器化：Docker 一键部署

## 技术栈

Python · FastAPI · LangGraph · LangChain · Chroma · 通义 text-embedding-v3 · DeepSeek · Docker

## 架构与数据流

**入库**：文档 → 解析成文本 → 分块 → 向量化 → 存入 Chroma（原文 + 向量 + 来源）

**问答**：提问 → Agent 决策 → 检索相关片段 → 生成带引用的回答

## 快速开始

### 1. 环境要求

- Python 3.14
- （可选）Docker

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API key
```

### 3. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. 启动服务

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 5. 使用

- 上传文档：`POST /upload`
- 提问：`POST /chat`
- Swagger 文档：浏览器打开 `http://localhost:8000/docs`

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/upload` | 上传 PDF/Word 文档并入库 |
| POST | `/chat` | 提问（question + 可选 thread_id） |

## 项目结构

```
docqa/
├── parse.py            # 文档解析（PDF/Word → 文本）
├── ingest.py           # 知识库构建（分块 + 向量化 + 入库）
├── agent.py            # LangGraph 问答 Agent（检索 + 防幻觉 + 多轮记忆）
├── server.py           # FastAPI 服务
├── requirements.txt    # 依赖清单
├── Dockerfile          # 容器化
└── .env.example        # 环境变量模板
```

## Docker 部署

```bash
docker build -t docqa .
docker run -d --name docqa -p 8000:8000 --env-file .env docqa
```