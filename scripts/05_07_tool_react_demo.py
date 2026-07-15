# scripts/05_07_tool_react_demo.py
"""05.07 Tool + ReAct 初体验演示。

【本课要感受的三件事】
1. @tool 函数自带 name / description / 参数 schema
2. 工具出错返回字符串，不把进程打崩
3. Agent 循环里能看见 get_inventory 被调用（trace）

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

from app.api.agent import (  # noqa: E402
    build_default_agent_runner,
    run_scripted_inventory_demo,
    run_tool_agent,
)
from app.models.factory import describe_provider, get_chat_model  # noqa: E402
from app.tools.inventory import get_inventory, get_shipment  # noqa: E402

# ======================== 可调开关 ========================

USE_CHAT = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
QUESTION = os.getenv(
    "AGENT_QUESTION",
    "耳机 Pro 黑色（EARPHONE-PRO-BK）还有货吗？还有多少件？",
)
NOTE_PATH = ROOT / "notes" / "tool_react_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("USE_CHAT:", USE_CHAT)
    print("question:", QUESTION)
    print("provider:", describe_provider())
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 05.07 Tool 与 ReAct 初体验 · 实跑记录\n",
        f"- USE_CHAT: `{USE_CHAT}`",
        f"- question: {QUESTION}",
        f"- provider: `{describe_provider().get('provider')}`",
        "",
    ]

    # ---- STEP 1 · Tool schema（说明书）----
    print("\n" + "=" * 52, "STEP 1 · Tool 说明书 / schema")
    print("name:", get_inventory.name)
    print("description:", get_inventory.description)
    print("args schema:", get_inventory.args)
    assert get_inventory.name == "get_inventory"
    assert "sku" in (get_inventory.args or {})
    assert "库存" in (get_inventory.description or "") or "sku" in (
        get_inventory.description or ""
    ).lower()
    print("shipment tool:", get_shipment.name, get_shipment.args)
    print("ASSERT: Tool 含清晰 name/描述/参数 → PASS")
    note.append("## STEP 1 · schema\n")
    note.append(f"- name: `{get_inventory.name}`")
    note.append(f"- description: {get_inventory.description}")
    note.append(f"- args: `{get_inventory.args}`\n")

    # ---- STEP 2 · 直接 invoke Tool（不经模型）----
    print("\n" + "=" * 52, "STEP 2 · 直接 invoke Tool")
    ok = get_inventory.invoke({"sku": "EARPHONE-PRO-BK"})
    zero = get_inventory.invoke({"sku": "EARPHONE-PRO-WH"})
    missing = get_inventory.invoke({"sku": "NO-SUCH"})
    print("BK:", ok)
    print("WH:", zero)
    print("missing:", missing)
    assert "stock=12" in ok
    assert "stock=0" in zero
    assert missing == "not_found"
    # 错误也是字符串
    empty = get_inventory.invoke({"sku": "  "})
    print("empty sku:", empty)
    assert empty.startswith("error:")
    print("ASSERT: Tool 可独立调用且错误可读 → PASS")
    note.append("## STEP 2 · 直接调用\n")
    note.append(f"- BK: `{ok}`")
    note.append(f"- WH: `{zero}`")
    note.append(f"- missing: `{missing}`\n")

    # ---- STEP 3 · 脚本化 / 真模型 Agent ----
    print("\n" + "=" * 52, "STEP 3 · Agent 循环（至少调 1 次 Tool）")
    if USE_CHAT:

        def _log(ev: dict) -> None:
            print(
                f"  step={ev['step']} tool_calls={ev['has_tool_calls']} "
                f"preview={ev['content_preview']!r}"
            )

        result = run_tool_agent(
            QUESTION,
            model=get_chat_model(temperature=0.1),
            tools=[get_inventory, get_shipment],
            max_steps=4,
            on_step=_log,
        )
    else:
        result = run_scripted_inventory_demo("EARPHONE-PRO-BK")
        print("thought:", result.get("thought"))

    print("mode:", result.get("mode"))
    print("trace:", result.get("trace"))
    print("answer:\n", result.get("answer"))
    assert result.get("trace"), "trace 不能为空"
    assert any(t.get("tool") == "get_inventory" for t in result["trace"])
    print("ASSERT: trace 中出现 get_inventory → PASS")
    note.append("## STEP 3 · Agent\n")
    note.append(f"- mode: `{result.get('mode')}`")
    note.append(f"- trace: `{result.get('trace')}`")
    note.append("```text\n" + str(result.get("answer")) + "\n```\n")

    # ---- STEP 4 · build_default_agent_runner 统一入口 ----
    print("\n" + "=" * 52, "STEP 4 · build_default_agent_runner")
    runner = build_default_agent_runner(use_chat=USE_CHAT)
    r2 = runner("CABLE-USB-C 还有多少库存？")
    print("trace:", r2.get("trace"))
    print("answer:", str(r2.get("answer"))[:240])
    assert any(t.get("tool") == "get_inventory" for t in r2.get("trace") or [])
    print("ASSERT: 统一入口也能调到 Tool → PASS")
    note.append("## STEP 4 · runner\n")
    note.append(f"- trace: `{r2.get('trace')}`")
    note.append("```text\n" + str(r2.get("answer"))[:400] + "\n```\n")

    note.append("## 结论\n")
    note.append("- Tool = 说明书 + 函数；描述写清何时用/不用。")
    note.append("- ReAct 初体验：Thought → Action(Tool) → Observation → Final Answer。")
    note.append("- 完整 Loop 工程（步数、超时、HITL）放 M06。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: tool_react 验收通过")


if __name__ == "__main__":
    main()
