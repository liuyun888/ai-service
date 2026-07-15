# scripts/06_01_agent_vs_chat_demo.py
"""06.01 Agent 是什么 · Chat vs Agent 对照演示。

【本课要感受的三件事】
1. 同一句「还有多少库存」：Chat 往往猜数；Agent 的 trace 里有 Tool
2. Agent ≈ Model + Tools + 控制策略（对照 05.07 源码标出三件套）
3. 不是所有事都该全自动（笔记三列：不该让 Agent 做的）

工作目录：必须在 ai-service/ 下。
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

from app.lessons.m06_01_agent_vs_chat import (  # noqa: E402
    NOTE_THREE_COLUMNS_EXAMPLE,
    ground_truth_stock,
    label_parts_for_05_07,
    run_agent_side,
    run_chat_only,
    run_chat_only_offline,
)
from app.models.factory import describe_provider, get_chat_model  # noqa: E402

# ======================== 可调开关 ========================

USE_CHAT = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
QUESTION = os.getenv(
    "DEMO_QUESTION",
    "耳机 Pro 黑色 EARPHONE-PRO-BK 现在仓库里还有多少件？请给准确数字。",
)
NOTE_PATH = ROOT / "notes" / "agent_vs_chat_result.md"
SKU = "EARPHONE-PRO-BK"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("USE_CHAT:", USE_CHAT)
    print("question:", QUESTION)
    print("provider:", describe_provider())
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    truth = ground_truth_stock(SKU)
    print("ground_truth (mock Tool):", truth)

    note: list[str] = [
        "# 06.01 Agent 是什么 · 实跑记录\n",
        f"- USE_CHAT: `{USE_CHAT}`",
        f"- question: {QUESTION}",
        f"- ground_truth: `{truth}`",
        f"- provider: `{describe_provider().get('provider')}`",
        "",
        "## 公式\n",
        "`Agent ≈ Model + Tools + 控制策略（Loop）`\n",
        "",
    ]

    # ---- STEP 1 · 回顾 05.07 三件套落点 ----
    print("\n" + "=" * 52, "STEP 1 · 标出 05.07 里的三件套")
    parts = label_parts_for_05_07()
    for k, v in parts.items():
        print(f"  - {k}: {v}")
    assert "Tool" in parts["Tools"] or "get_inventory" in parts["Tools"]
    print("ASSERT: 能指认 Model / Tools / Loop → PASS")
    note.append("## STEP 1 · 三件套落点\n")
    for k, v in parts.items():
        note.append(f"- **{k}**: {v}")
    note.append("")

    # ---- STEP 2 · Chat only ----
    print("\n" + "=" * 52, "STEP 2 · 纯 Chat（无 Tool）")
    if USE_CHAT:
        model = get_chat_model(temperature=0.7)
        chat = run_chat_only(QUESTION, model=model)
    else:
        chat = run_chat_only_offline(QUESTION)
    print("mode:", chat["mode"])
    print("trace:", chat["trace"])
    print("answer:\n", chat["answer"][:400])
    assert chat["trace"] == []
    assert chat["used_tools"] is False
    print("ASSERT: Chat 路径 trace 为空 → PASS")
    note.append("## STEP 2 · Chat only\n")
    note.append(f"- mode: `{chat['mode']}`")
    note.append(f"- trace: `{chat['trace']}`")
    note.append("```text\n" + str(chat["answer"])[:500] + "\n```\n")

    # ---- STEP 3 · Agent ----
    print("\n" + "=" * 52, "STEP 3 · Agent（有 Tool + Loop）")
    model_a = get_chat_model(temperature=0.1) if USE_CHAT else None
    agent = run_agent_side(QUESTION, model=model_a, use_chat=USE_CHAT)
    print("mode:", agent.get("mode"))
    print("trace:", agent.get("trace"))
    print("answer:\n", str(agent.get("answer"))[:400])
    assert agent.get("trace"), "Agent 应至少调用 1 次 Tool"
    assert any(t.get("tool") == "get_inventory" for t in agent["trace"])
    # 真值应对齐 mock（Agent 侧 observation 含 stock=12）
    obs = " ".join(str(t.get("observation", "")) for t in agent["trace"])
    assert "stock=12" in obs or "12" in str(agent.get("answer"))
    print("ASSERT: Agent trace 含 get_inventory，数字可对齐 mock → PASS")
    note.append("## STEP 3 · Agent\n")
    note.append(f"- mode: `{agent.get('mode')}`")
    note.append(f"- trace: `{agent.get('trace')}`")
    note.append("```text\n" + str(agent.get("answer"))[:500] + "\n```\n")

    # ---- STEP 4 · 对照结论 + 笔记三列模板 ----
    print("\n" + "=" * 52, "STEP 4 · 对照与笔记三列")
    print("差异一句话: Chat 无 tool 轨迹；Agent 先 Action 再答，数字拴在 Observation 上。")
    print("笔记三列示例（请改成你自己的）:")
    for col, items in NOTE_THREE_COLUMNS_EXAMPLE.items():
        print(f"  [{col}]")
        for it in items:
            print(f"    - {it}")
    note.append("## STEP 4 · 对照\n")
    note.append(
        "| | Chat | Agent |\n|---|---|---|\n"
        "| 工具轨迹 | 无 | 有 get_inventory |\n"
        f"| 与 mock 真值 | 易编造/漂移 | Observation=`{truth}` |\n"
        "| 形态 | 一次生成结束 | 思考→调工具→观察→再答 |\n"
    )
    note.append("\n## 笔记三列（示例，请改成自己的）\n")
    note.append("### Chat 能做\n")
    for it in NOTE_THREE_COLUMNS_EXAMPLE["chat_ok"]:
        note.append(f"- {it}")
    note.append("\n### Agent 才需要\n")
    for it in NOTE_THREE_COLUMNS_EXAMPLE["agent_needed"]:
        note.append(f"- {it}")
    note.append("\n### 不该让 Agent 全自动做\n")
    for it in NOTE_THREE_COLUMNS_EXAMPLE["should_not_auto"]:
        note.append(f"- {it}")
    note.append("")
    note.append("## 结论\n")
    note.append("- Agent 不是「更强的模型」，是 Model + Tools + 控制策略。")
    note.append("- 05.07 调一次 Tool 是最小形态；本模块会把 Loop 跑稳。")
    note.append("- 不可逆操作默认不要全自动。")
    note.append("")
    print("ASSERT: 对照表已写入笔记 → PASS")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: agent_vs_chat 验收通过")


if __name__ == "__main__":
    main()
