# app/lessons/m07_07_multiagent_workflow.py
"""课次 07.07 · 多步工作流包装：角色表、低/高风险验收、对照行业说明。"""

from __future__ import annotations

from typing import Any

from app.graphs.workflow import (
    resume_high_risk,
    run_high_risk_pause,
    run_low_risk,
    structured_result,
)


def role_catalog() -> list[dict[str, str]]:
    """哪个节点是角色、干什么。"""
    return [
        {"role": "受理员", "node": "intake", "job": "登记诉求 → intake_notes"},
        {"role": "核查员", "node": "gather_evidence", "job": "订单 mock + 政策证据 → evidence"},
        {"role": "风控员", "node": "assess_risk", "job": "规则打 risk_level"},
        {"role": "审核员", "node": "human_review", "job": "高风险 HITL interrupt"},
        {"role": "执行员", "node": "execute_or_skip", "job": "开单 mock / 驳回"},
        {"role": "话术员", "node": "draft_reply", "job": "只基于 State 写 user_message"},
    ]


def gate_edges() -> list[str]:
    """门禁边（条件路由 + HITL）。"""
    return [
        "assess_risk → human_review | execute_or_skip（按 risk_level）",
        "human_review 内 interrupt（高风险人工门禁）",
    ]


def industry_analogs() -> list[dict[str, str]]:
    """对照：预问诊 / 材料预审（同构图）。"""
    return [
        {
            "industry": "预问诊",
            "map": "主诉采集→红旗规则→医生确认→就诊建议",
        },
        {
            "industry": "材料预审",
            "map": "收件→缺件检测→人工抽检→通知补正",
        },
    ]


def demo_low() -> dict[str, Any]:
    return run_low_risk("七天无理由退货", case_id="R-1", thread_id="wf-low-demo")


def demo_high_approve() -> dict[str, Any]:
    paused = run_high_risk_pause(
        "破损要全额退款", case_id="R-2", thread_id="wf-high-demo"
    )
    done = resume_high_risk(
        paused["app"], "wf-high-demo", approved=True, reviewer="ops_01", note="同意"
    )
    return {"paused": paused, "done": done}


def demo_high_reject() -> dict[str, Any]:
    paused = run_high_risk_pause(
        "破损要全额退款并要投诉", case_id="R-3", thread_id="wf-high-rej"
    )
    done = resume_high_risk(
        paused["app"], "wf-high-rej", approved=False, reviewer="ops_02", note="材料不足"
    )
    return {"paused": paused, "done": done}
