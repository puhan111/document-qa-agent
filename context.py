# -*- coding: utf-8 -*-
"""对话上下文压缩：控制多轮对话历史 token 膨胀。

说明：这里用字符数估算 token（中文≈1字≈1token，英文近似），零依赖、成本低；
生产环境可换 tiktoken 做精确统计。
注意：压缩按「完整用户轮次」切，绝不切断 工具调用(AI tool_calls <-> Tool) 这一对，
否则 LLM 会报 "tool must be a response to tool_calls"。
"""
import os
import logging

from langchain_core.messages import SystemMessage, RemoveMessage, HumanMessage

logger = logging.getLogger(__name__)

CONTEXT_MAX_CHARS = int(os.getenv("CONTEXT_MAX_CHARS", "8000"))
CONTEXT_KEEP_RECENT = int(os.getenv("CONTEXT_KEEP_RECENT", "6"))   # 保留最近 N 轮（每轮从一个 Human 开始）


def _count_chars(messages) -> int:
    """统计 messages 的总字符数（近似 token 数）。"""
    return sum(len(str(getattr(m, "content", ""))) for m in messages)


def _is_human(m) -> bool:
    return isinstance(m, HumanMessage)


def _summarize(messages, llm) -> str:
    """把旧对话交给模型压缩成一段中文摘要（temperature=0，减少发散）。"""
    joined = "\n".join(f"{type(m).__name__}: {m.content}" for m in messages)
    prompt = (
        "请把下面这段对话压缩成一段不超过 100 字的中文摘要，"
        "保留关键事实、用户问过的问题，不要添加新内容：\n\n" + joined
    )
    resp = llm.bind(temperature=0).invoke([SystemMessage(content=prompt)])
    return str(resp.content).strip()


def compress_history(messages, llm):
    """检查是否需要压缩。返回 (update, model_prefix) 或 (None, None)。

    - update: 给 LangGraph 的消息更新（RemoveMessage 删旧 + 摘要消息），让持久层也瘦身
    - model_prefix: 本轮真正发给模型的「摘要 + 最近 N 轮」（不含系统提示词）
    """
    if len(messages) <= 1:
        return None, None
    if _count_chars(messages) <= CONTEXT_MAX_CHARS:
        return None, None

    # 找到所有用户轮次的起点（Human 消息）
    human_idx = [i for i, m in enumerate(messages) if _is_human(m)]
    if len(human_idx) <= CONTEXT_KEEP_RECENT:
        return None, None

    # 保留最近的 CONTEXT_KEEP_RECENT 轮，更早的整轮提出来做摘要
    start = human_idx[-CONTEXT_KEEP_RECENT]
    recent = messages[start:]
    old = messages[:start]
    before = _count_chars(messages)

    try:
        summary_text = _summarize(old, llm)
        summary_msg = SystemMessage(content=f"（此前对话摘要）{summary_text}")
        update = [RemoveMessage(id=m.id) for m in old] + [summary_msg]
        model_prefix = [summary_msg] + recent
        logger.info("触发上下文压缩：%d 字 → 摘要 + 近%d轮", before, CONTEXT_KEEP_RECENT)
        return update, model_prefix
    except Exception as e:  # 降级：摘要失败，直接删掉最旧的整轮
        logger.warning("摘要生成失败(%s)，降级为删除最旧轮次", e)
        update = [RemoveMessage(id=m.id) for m in old]
        logger.info("降级截断：%d 字 → %d 字", before, _count_chars(recent))
        return update, list(recent)