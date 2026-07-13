# scripts/03_01_rag_vs_llm.py
"""03.01 为什么需要 RAG：同一问题对比「纯 LLM」与「带权威资料再答」。

【你要看懂的一件事】
大模型会「流畅地编」——没给依据时，它可能报一个听起来合理、
却与你说明书不符的数字。

RAG 的第一步（本课简化版）：先把权威片段塞进 Prompt，再要求
「只根据资料回答；资料没有就说不知道」——让事实以外部为准。

本课还不做向量检索（那是 03.04+）；这里用手工给的 SNIPPET 模拟
「检索已经找到了正确段落」。
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.llm.client import call_chat, default_model  # noqa: E402

# ======================== 可调开关 ========================

# False：只打印两份 Prompt，不调 Chat（没 Key 也能看对比结构）
USE_CHAT = True

# 纯 LLM 多跑几轮，观察措辞/数字是否漂移（temperature 偏高时更明显）
PLAIN_REPEATS = 2

# ======================== 本课固定用例 ========================

QUESTION = "降噪耳机 Pro 的续航是多久？"

# 「权威外部知识」：故意用 30 / 45，与网上常见「28 小时」等区分开
SNIPPET = (
    "【说明书摘录·降噪耳机 Pro】"
    "降噪开启时续航约 30 小时；关闭降噪时续航约 45 小时。"
    "（本数据仅适用于 Pro 型号，非其他型号。）"
)

# 资料里「正确」的数字（用于自动标注是否 grounded）
DOC_NUMBERS = ("30", "45")

# 常见「像真的」但不在你文档里的数字（用于标注可能的幻觉）
COMMON_WRONG = ("28", "24", "32", "40", "48")


def build_plain_prompt() -> str:
    """纯 LLM：只给问题，不给任何说明书。"""
    return f"请回答：{QUESTION}"


def build_rag_prompt() -> str:
    """带资料 RAG（本课简化）：手工片段 + 硬约束，模拟检索后的 Augment。"""
    return (
        "你是产品客服助手。\n"
        "规则：\n"
        "1. 只根据下列「资料」回答，禁止编造资料中没有的数字。\n"
        "2. 若资料不足以回答，必须明确说「资料中没有相关信息」。\n"
        "3. 回答时请引用资料中的具体数字。\n\n"
        f"资料：\n{SNIPPET}\n\n"
        f"问题：{QUESTION}\n"
    )


def analyze_answer(label: str, text: str) -> dict[str, object]:
    """粗判回答是否「贴资料」：是否出现文档数字 / 常见错数。

    说明：这是教学用启发式，不是生产级幻觉检测。
    """
    nums = re.findall(r"\d+", text)
    has_doc = any(n in text for n in DOC_NUMBERS)
    wrong_hits = [n for n in COMMON_WRONG if n in text and n not in DOC_NUMBERS]
    return {
        "label": label,
        "has_doc_numbers": has_doc,
        "wrong_like_numbers": wrong_hits,
        "all_numbers": nums[:8],  # 只展示前几个，避免刷屏
    }


def call_once(prompt: str, *, temperature: float) -> tuple[str, float]:
    """调一次 Chat，返回 (回答, 耗时毫秒)。"""
    t0 = time.perf_counter()
    ans = call_chat([{"role": "user", "content": prompt}], temperature=temperature)
    ms = (time.perf_counter() - t0) * 1000
    return ans, ms


def main() -> None:
    plain = build_plain_prompt()
    rag = build_rag_prompt()

    print("=" * 40, "CONFIG")
    print("chat_model:", default_model() if USE_CHAT else "(skipped)")
    print("USE_CHAT:", USE_CHAT)
    print("QUESTION:", QUESTION)
    print("DOC_NUMBERS:", DOC_NUMBERS)

    print("=" * 40, "PROMPTS")
    print("--- 纯 LLM ---\n", plain)
    print("--- 带资料 RAG ---\n", rag[:280], "...")

    note: list[str] = [
        "# 纯 LLM vs 带资料 RAG 实跑对比\n\n",
        f"- 问题：{QUESTION}\n",
        f"- 权威资料：`{SNIPPET}`\n",
        f"- Chat：`{default_model() if USE_CHAT else 'skipped'}`\n\n",
    ]

    rag_ans = ""
    rag_analysis: dict[str, object] = {}

    if USE_CHAT:
        # ----- 纯 LLM：可能给出「常见但不在文档里」的数字 -----
        print("\n" + "=" * 40, "纯 LLM（无资料）")
        note.append("## 纯 LLM\n\n")
        for i in range(PLAIN_REPEATS):
            ans, ms = call_once(plain, temperature=0.7)
            info = analyze_answer(f"plain_{i+1}", ans)
            print(f"--- round {i + 1} ({ms:.0f} ms) ---")
            print("ANSWER:\n", ans)
            print("分析:", info)
            note.append(f"### round {i + 1}（{ms:.0f} ms）\n\n{ans}\n\n")
            note.append(f"- 分析：{info}\n\n")

        # ----- 带资料：应能复述 30 / 45 -----
        print("\n" + "=" * 40, "带资料 RAG（有片段约束）")
        rag_ans, ms = call_once(rag, temperature=0.1)
        rag_analysis = analyze_answer("rag", rag_ans)
        print(f"耗时 {ms:.0f} ms")
        print("ANSWER:\n", rag_ans)
        print("分析:", rag_analysis)

        note.append("## 带资料 RAG\n\n")
        note.append(f"耗时 {ms:.0f} ms\n\n{rag_ans}\n\n")
        note.append(f"- 分析：{rag_analysis}\n\n")

        # 验收：带资料路径必须提到文档里的 30（45 可选但通常也会提）
        assert rag_analysis["has_doc_numbers"], (
            f"带资料应答应含文档数字 {DOC_NUMBERS}，实际：{rag_ans[:200]}"
        )
        print("\nASSERT: 带资料含文档数字 → PASS")
    else:
        print("\nUSE_CHAT=False：跳过真实 Chat，仅展示 Prompt 对比。")
        note.append("（未调 Chat，仅 Prompt 对比）\n\n")

    note.append("## 结论\n\n")
    note.append(
        "- **参数知识**：模型权重里的常识/语言能力；可能「像真的」但不等于你的说明书。\n"
        "- **外部知识**：SNIPPET / 文档 / 向量库；业务事实应以外部为准。\n"
        "- **RAG 动机**：先取资料再生成，把「必须有依据」变成默认流程。\n"
        "- 本课是「手工片段」版 RAG；下一课起会拆 Index / Retrieve / Augment / Generate。\n"
    )

    out = ROOT / "notes" / "rag_vs_llm_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(note), encoding="utf-8")
    print(f"\n记录已写入：{out}")


if __name__ == "__main__":
    main()
