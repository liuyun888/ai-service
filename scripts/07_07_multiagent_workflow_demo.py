# scripts/07_07_multiagent_workflow_demo.py
"""07.07 多智能体与多步工作流演示。

【本课要感受的三件事】
1. 角色是节点，交接在 State，不是群聊
2. 低风险自动通；高风险 interrupt 后再 resume
3. 最终 structured_result 可给 BFF/工单，不只一段散文

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m07_07_multiagent_workflow import (  # noqa: E402
    demo_high_approve,
    demo_high_reject,
    demo_low,
    gate_edges,
    industry_analogs,
    role_catalog,
)

NOTE_PATH = ROOT / "notes" / "multiagent_workflow_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("M07 里程碑：多步图 + HITL + 结构化结果")
    print("ROOT =", ROOT)

    note: list[str] = [
        "# 07.07 多智能体与多步工作流 · 实跑记录\n",
        "",
        "```text",
        "intake → gather_evidence → assess_risk",
        "  → human_review(HITL) | execute_or_skip → draft_reply",
        "```",
        "",
    ]

    # ---- STEP 1 · 角色与门禁 ----
    print("\n" + "=" * 52, "STEP 1 · 角色节点与门禁边")
    roles = role_catalog()
    for r in roles:
        print(f"  [{r['role']}] {r['node']}: {r['job']}")
    for g in gate_edges():
        print("  GATE:", g)
    assert len(roles) == 6
    print("ASSERT: 六角色 + 门禁可指出 → PASS")
    note.append("## STEP 1 · 角色\n")
    note.append("| 角色 | 节点 | 职责 |")
    note.append("|------|------|------|")
    for r in roles:
        note.append(f"| {r['role']} | {r['node']} | {r['job']} |")
    note.append("")
    for g in gate_edges():
        note.append(f"- 门禁: {g}")
    note.append("")

    # ---- STEP 2 · 低风险 ----
    print("\n" + "=" * 52, "STEP 2 · 低风险自动通")
    low = demo_low()
    st = low["structured"]
    print("path:", st.get("path"))
    print("roles:", st.get("role_handoff"))
    print("decision:", st.get("decision"), "|", st.get("action_result"))
    print("msg:", (st.get("user_message") or "")[:160])
    assert low["interrupted"] is False
    assert "human_review" not in (st.get("path") or [])
    assert st.get("decision") == "auto_pass"
    assert st.get("action_result") == "mock_return_created"
    assert st.get("user_message")
    assert "evidence" in st and st["evidence"]
    print("ASSERT: 低风险无人审批到最终话术 → PASS")
    note.append("## STEP 2 · 低风险\n")
    note.append("```json")
    note.append(json.dumps(st, ensure_ascii=False, indent=2))
    note.append("```\n")

    # ---- STEP 3 · 高风险暂停 ----
    print("\n" + "=" * 52, "STEP 3 · 高风险暂停（未批准）")
    # 复用 approve demo 的 paused 前半：单独再 pause 一次
    from app.graphs.workflow import run_high_risk_pause

    paused_only = run_high_risk_pause(
        "破损要全额退款", case_id="R-wait", thread_id="wf-wait-only"
    )
    print("interrupted:", paused_only["interrupted"])
    print("next:", paused_only["next"])
    print("path:", paused_only["values"].get("path"))
    assert paused_only["interrupted"] is True
    assert "human_review" in paused_only["next"]
    assert "execute_or_skip" not in (paused_only["values"].get("path") or [])
    print("ASSERT: 高风险 WAITING / interrupt → PASS")
    note.append("## STEP 3 · 高风险暂停\n")
    note.append(f"- next: `{paused_only['next']}`")
    note.append(f"- path: `{paused_only['values'].get('path')}`\n")

    # ---- STEP 4 · 批准后续跑 ----
    print("\n" + "=" * 52, "STEP 4 · 高风险批准 → 结构化结果")
    appr = demo_high_approve()
    s = appr["done"]["structured"]
    print("path:", s.get("path"))
    print("structured:", json.dumps(s, ensure_ascii=False)[:240])
    assert "human_review" in (s.get("path") or [])
    assert "execute_or_skip" in (s.get("path") or [])
    assert s.get("decision") == "approved"
    assert s.get("action_result") == "mock_return_created"
    assert s.get("case_id") == "R-2"
    assert s.get("user_message")
    # 话术不得声称没进 evidence 的发货承诺（弱校验：不出现瞎编关键字）
    assert "保证明天" not in (s.get("user_message") or "")
    print("ASSERT: 批准后结构化字段齐全 → PASS")
    note.append("## STEP 4 · 批准\n")
    note.append("```json")
    note.append(json.dumps(s, ensure_ascii=False, indent=2))
    note.append("```\n")

    # ---- STEP 5 · 驳回 ----
    print("\n" + "=" * 52, "STEP 5 · 高风险驳回")
    rej = demo_high_reject()
    rs = rej["done"]["structured"]
    print("decision:", rs.get("decision"), "|", rs.get("action_result"))
    print("msg:", (rs.get("user_message") or "")[:120])
    assert rs.get("decision") == "rejected"
    assert rs.get("action_result") == "rejected"
    assert "未创建退货单" in (rs.get("user_message") or "")
    print("ASSERT: 驳回路径明确 → PASS")
    note.append("## STEP 5 · 驳回\n")
    note.append(f"- `{rs}`\n")

    # ---- STEP 6 · 行业对照 ----
    print("\n" + "=" * 52, "STEP 6 · 同构对照（预问诊/材料预审）")
    for row in industry_analogs():
        print(f"  {row['industry']}: {row['map']}")
    print("ASSERT: 能口述同构图 → PASS")
    note.append("## STEP 6 · 对照\n")
    for row in industry_analogs():
        note.append(f"- {row['industry']}: {row['map']}")
    note.append("")

    note.append("## 结论\n")
    note.append("- 多智能体在工程上 = 多角色节点 + State 交接 + 图门禁。")
    note.append("- M07 里程碑：多步图可跑，高风险可暂停，结果可结构化交付。")
    note.append("- 下一模块：Harness / Deep Agents 运行时外壳。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: multiagent_workflow 验收通过")


if __name__ == "__main__":
    main()
