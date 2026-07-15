# scripts/05_01_hello_chain_demo.py
"""05.01 LangChain / LCEL 最小链演示。

【本课要感受的三件事】
1. prompt | model | parser 用 | 串起来，统一 chain.invoke(...)
2. 可拆开逐节 invoke，方便调试（链不神秘）
3. USE_CHAT=0 时换离线 Runnable，水管接口不变（为 05.02 工厂打样）

依赖：langchain-core、langchain-openai（见 requirements.txt）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.chains.hello_chain import (  # noqa: E402
    HELLO_PROMPT,
    build_hello_chain,
    make_chat_model,
    make_offline_model,
    run_hello,
)
from app.llm.client import default_model  # noqa: E402

# ======================== 可调开关 ========================

# False：不调远端 Chat，用离线 Runnable（仍走完整 LCEL）
USE_CHAT = os.getenv("USE_CHAT", "1").strip().lower() in {"1", "true", "yes", "on"}

TOPIC = os.getenv("HELLO_TOPIC", "什么是 RAG")
NOTE_PATH = ROOT / "notes" / "hello_chain_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("USE_CHAT:", USE_CHAT)
    print("topic:", TOPIC)
    print("chat_model:", default_model() if USE_CHAT else "(offline Runnable)")

    note: list[str] = [
        "# 05.01 LangChain 与 LCEL · 实跑记录\n",
        f"- USE_CHAT: `{USE_CHAT}`",
        f"- topic: {TOPIC}",
        f"- model: `{default_model() if USE_CHAT else 'offline'}`",
        "",
    ]

    # ---- STEP 1 · 逐节拆开看数据长什么样 ----
    print("\n" + "=" * 52, "STEP 1 · 拆开水管逐节 invoke")
    prompt_value = HELLO_PROMPT.invoke({"topic": TOPIC})
    print("【Prompt 输出类型】", type(prompt_value).__name__)
    # messages 可读预览
    msgs = prompt_value.to_messages()
    for m in msgs:
        role = m.type
        content = str(m.content)[:120]
        print(f"  - {role}: {content}")

    model = make_chat_model() if USE_CHAT else make_offline_model()
    ai_msg = model.invoke(msgs)
    print("【Model 输出类型】", type(ai_msg).__name__)
    raw = getattr(ai_msg, "content", ai_msg)
    print("【Model 原文】", str(raw)[:300])

    from langchain_core.output_parsers import StrOutputParser

    parsed = StrOutputParser().invoke(ai_msg)
    print("【Parser 输出类型】", type(parsed).__name__)
    print("【Parser 纯文本】", parsed[:300])
    assert isinstance(parsed, str) and parsed.strip(), "Parser 应产出非空 str"
    print("ASSERT: 三节都能单独 invoke → PASS")

    note.append("## STEP 1 · 逐节\n")
    note.append(f"- Prompt → `{type(prompt_value).__name__}`")
    note.append(f"- Model → `{type(ai_msg).__name__}`")
    note.append(f"- Parser → str，前 200 字：{parsed[:200]}")
    note.append("")

    # ---- STEP 2 · 整条链一把 invoke ----
    print("\n" + "=" * 52, "STEP 2 · 整链 invoke（prompt | model | parser）")
    chain = build_hello_chain(model)
    text = chain.invoke({"topic": TOPIC})
    print(text)
    assert isinstance(text, str) and len(text.strip()) >= 10
    # 离线或真模型都应谈到检索/RAG 相关直觉（宽松）
    if not USE_CHAT:
        assert "检索" in text or "RAG" in text.upper() or "资料" in text
    print("ASSERT: 整链返回非空字符串 → PASS")

    note.append("## STEP 2 · 整链\n")
    note.append("```text")
    note.append(text)
    note.append("```")
    note.append("")

    # ---- STEP 3 · 换 topic 再跑（骨架不变）----
    print("\n" + "=" * 52, "STEP 3 · 换 topic（退货时效）")
    text2 = run_hello("退货时效", use_chat=USE_CHAT)
    print(text2)
    assert isinstance(text2, str) and text2.strip()
    print("ASSERT: 同一条链换 topic 可复用 → PASS")

    note.append("## STEP 3 · 换 topic\n")
    note.append("```text")
    note.append(text2)
    note.append("```")
    note.append("")
    note.append("## 结论\n")
    note.append("- LangChain 属于专栏三层里的 Framework 层。")
    note.append("- LCEL：`prompt | model | parser`，统一 `invoke`。")
    note.append("- 调试时先逐节 invoke，再合成整链。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: hello_chain LCEL 验收通过")


if __name__ == "__main__":
    main()
