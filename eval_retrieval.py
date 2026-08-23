"""检索评测：检查 search_docs 对一组问题的命中率。"""
from agent import search_docs

CASES = [
    ("退货政策是什么", "7 天"),
    ("客服电话是多少", "400-123-4567"),
    ("工作时间是几点到几点", "9:00"),
]

hits = 0
for question, keyword in CASES:
    result = search_docs.invoke({"query": question})
    ok = keyword in result
    if ok:
        hits += 1
    print(f"[{'命中' if ok else '未命中'}] 问题：{question}")
    if not ok:
        print(f"         预期关键词：{keyword}")
        print(f"         实际结果：{result[:100]}")

total = len(CASES)
print(f"\n检索命中率：{hits}/{total}")
