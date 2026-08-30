# -*- coding: utf-8 -*-
"""验收：连续多轮长对话，观察历史字符数在压缩后是否回落。"""
import os
os.environ["CONTEXT_MAX_CHARS"] = "800"      # 演示时压低阈值，确保能触发压缩
os.environ["CONTEXT_KEEP_RECENT"] = "4"      # 保留更少，更容易观察到回落

from agent import graph, ask
from context import _count_chars


def snapshot(thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    st = graph.get_state(config)
    msgs = st.values.get("messages", [])
    return _count_chars(msgs), len(msgs)


if __name__ == "__main__":
    thread = "demo_compress"
    questions = [
        "请完整说明退货政策、客服电话和工作时间。",
        "再讲一遍退货政策，并把客服电话和工作时间也列出来。",
        "如果要在7天内退货，具体流程是什么？运费谁出？",
        "客服电话是多少？周末上班吗？",
        "工作时间是几点到几点？我该几点打？",
        "退货后多久能退款？需要什么凭证？",
        "如果商品用坏了，能退吗？",
        "保修是多久？人为损坏算吗？",
        "我再确认一下，签收后7天无理由退货，对吗？",
        "那退货要填什么单子？找谁？",
        "客服电话400开头那个，是多少来着？",
        "工作时间晚上也上班吗？我下班后能打吗？",
        "把之前所有信息再总结一遍。",
        "再说一次退货政策、电话、工作时间。",
        "最后确认：7天无理由 + 400电话 + 9点到21点，对吗？",
    ]
    for i, q in enumerate(questions, 1):
        try:
            ask(q, thread)
        except Exception as e:
            print(f"第{i}轮 出错：{e}")
        chars, n = snapshot(thread)
        print(f"第{i:2d}轮  历史字符数={chars:5d}  消息数={n:2d}")

    print("\n-------- 验证摘要是否保留关键信息 --------")
    ans = ask("我还是想问，退货是几天内无理由？", thread)
    print("恢复回答：", ans)