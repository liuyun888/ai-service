# scripts/07_06_hitl_demo.py
"""07.06 图内 HITL 演示。

【本课要感受的三件事】
1. interrupt 让图真正停住；未审批不会进 execute
2. 同一 thread_id + Command(resume) 可批准或驳回
3. 写入只在批准后；驳回路径明确且无写入

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m07_06_hitl import (  # noqa: E402
    bff_contract_notes,
    demo_no_execute_while_waiting,
    demo_pause_then_approve,
    demo_pause_then_reject,
)

NOTE_PATH = ROOT / "notes" / "hitl_graph_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("HITL = interrupt + Checkpointer + Command(resume)")
    print("ROOT =", ROOT)

    note: list[str] = [
        "# 07.06 HITL（图内）· 实跑记录\n",
        "",
        "```text",
        "validate_order → prepare_summary → human_review",
        "  → execute_refund | reject_notify",
        "```",
        "",
    ]

    # ---- STEP 1 · 暂停时不执行写入 ----
    print("\n" + "=" * 52, "STEP 1 · 未审批：停在 human_review")
    wait = demo_no_execute_while_waiting()
    print("interrupted:", wait["paused"]["interrupted"])
    print("next:", wait["paused"]["next"])
    print("path:", wait["path"])
    print("result:", wait["paused"]["values"].get("result"))
    print("interrupt_value:", wait["paused"].get("interrupt_value"))
    assert wait["paused"]["interrupted"] is True
    assert "human_review" in wait["paused"]["next"]
    assert wait["has_execute"] is False
    assert wait["paused"]["values"].get("executed_write") is False
    print("ASSERT: 暂停且未进 execute → PASS")
    note.append("## STEP 1 · 暂停\n")
    note.append(f"- next: `{wait['paused']['next']}`")
    note.append(f"- path: `{wait['path']}`")
    note.append(f"- interrupt: `{wait['paused'].get('interrupt_value')}`\n")

    # ---- STEP 2 · 批准后写入 ----
    print("\n" + "=" * 52, "STEP 2 · 批准 → execute_refund")
    appr = demo_pause_then_approve()
    done = appr["done"]["values"]
    print("path:", done.get("path"))
    print("result:", done.get("result"))
    print("executed_write:", done.get("executed_write"))
    assert "human_review" in (done.get("path") or [])
    assert "execute_refund" in (done.get("path") or [])
    assert done.get("executed_write") is True
    assert "已执行退货" in (done.get("result") or "")
    assert "reject_notify" not in (done.get("path") or [])
    print("ASSERT: 批准后才写入 → PASS")
    note.append("## STEP 2 · 批准\n")
    note.append(f"- path: `{done.get('path')}`")
    note.append(f"- result: {done.get('result')}\n")

    # ---- STEP 3 · 驳回无写入 ----
    print("\n" + "=" * 52, "STEP 3 · 驳回 → 明确结果、无写入")
    rej = demo_pause_then_reject()
    rv = rej["done"]["values"]
    print("path:", rv.get("path"))
    print("result:", rv.get("result"))
    print("executed_write:", rv.get("executed_write"))
    assert "reject_notify" in (rv.get("path") or [])
    assert "execute_refund" not in (rv.get("path") or [])
    assert rv.get("executed_write") is False
    assert "未执行任何写入" in (rv.get("result") or "")
    print("ASSERT: 驳回路径干净 → PASS")
    note.append("## STEP 3 · 驳回\n")
    note.append(f"- path: `{rv.get('path')}`")
    note.append(f"- result: {rv.get('result')}\n")

    # ---- STEP 4 · checkpointer + thread_id ----
    print("\n" + "=" * 52, "STEP 4 · 固定 thread_id 才能 resume")
    print("pause 用 thread_id=hitl-approve-1，resume 同 id（见 demo 源码）")
    assert appr["paused"]["config"]["configurable"]["thread_id"]
    print("thread:", appr["paused"]["config"]["configurable"]["thread_id"])
    print("ASSERT: checkpointer + thread_id 已使用 → PASS")
    note.append("## STEP 4 · thread_id\n")
    note.append("- resume 必须与 pause 使用同一 `thread_id`\n")

    # ---- STEP 5 · BFF 契约 ----
    print("\n" + "=" * 52, "STEP 5 · 与 BFF/前端的契约")
    for line in bff_contract_notes():
        print(" -", line)
    print("ASSERT: 契约可口述 → PASS")
    note.append("## STEP 5 · BFF 契约\n")
    for line in bff_contract_notes():
        note.append(f"- {line}")
    note.append("")

    note.append("## 结论\n")
    note.append("- 图内 interrupt 把 HITL 做成一等公民；配合 Checkpointer 可跨天审批。")
    note.append("- 写入类动作锁在批准之后；驳回要响亮，不要静默。")
    note.append("- 下一课：多智能体 + 多步工作流端到端。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: hitl_graph 验收通过")


if __name__ == "__main__":
    main()
