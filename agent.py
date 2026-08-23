import os
from dotenv import load_dotenv
from contextlib import ExitStack

import chromadb
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver

from ingest import embed_text

load_dotenv()


# 1. 检索工具：模型需要查资料时调用它
@tool
def search_docs(query: str) -> str:
    """在知识库里检索相关文档片段。参数 query 是用户的问题或要查的关键信息。"""
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="docs")

    q_vec = embed_text(query)
    result = collection.query(query_embeddings=[q_vec], n_results=3)

    docs = result["documents"][0]
    metas = result["metadatas"][0]

    parts = []
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        source = meta.get("source", "unknown")
        parts.append(f"[{i}]（来源：{source}）\n{doc}")
    return "\n\n".join(parts)


# 2. 模型：接 DeepSeek，temperature 调低减少幻觉
llm = ChatOpenAI(
    model=os.getenv("MODEL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    temperature=0.1,
)

# 3. 系统提示词：只按资料答 + 带出处 + 不知道就说不知道
SYSTEM_PROMPT = (
    "你是一个企业知识库问答助手。请只根据检索到的资料回答用户问题。"
    "如果资料里没有相关信息，就直接回答'根据现有资料无法回答'，不要编造或猜测。"
    "回答时请引用资料编号（例如 [1]）说明依据。"
)

llm_with_tools = llm.bind_tools([search_docs])


# 4. 图节点：调用模型（带上系统提示词 + 历史消息）
def chatbot(state: MessagesState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    return {"messages": [llm_with_tools.invoke(messages)]}


graph_builder = StateGraph(MessagesState)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode([search_docs]))
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

# 用 ExitStack 让 SQLite 连接在整个服务期间一直保持打开
_checkpoint_stack = ExitStack()
memory = _checkpoint_stack.enter_context(SqliteSaver.from_conn_string("checkpoints.sqlite"))
graph = graph_builder.compile(checkpointer=memory)


# 5. 问答入口（多轮）
def ask(question, thread_id="default"):
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [HumanMessage(content=question)]}, config)
    return result["messages"][-1].content


if __name__ == "__main__":
    print("多轮问答开始，输入 exit 退出")
    while True:
        q = input("你：")
        if q.lower() in ("exit", "quit"):
            break
        print("Agent：", ask(q))
