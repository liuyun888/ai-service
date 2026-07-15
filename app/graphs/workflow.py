# app/graphs/workflow.py
"""课次 07.07 · 多智能体与多步工作流：退货审核端到端。

务实定义「多智能体」：
- 每个角色 = 一个节点（不同职责 + 可选不同 Tool）
- 交接 = 写入共享 State 的结构化字段
- 编排 = 边 / 条件边 + 高风险 HITL（interrupt）

拓扑：
  intake → gather_evidence → assess_risk
        → (high? human_review : execute_or_skip)
        → draft_reply → END

里程碑：低风险无人审批到最终话术；高风险暂停批准后续跑；结果可 JSON 化。
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.tools.knowledge import search_knowledge

Risk = Literal["low", "medium", "high"]


class WFState(TypedDict, total=False):
    """退货工作流共享 State（角色交接全写在这里）。"""

    case_id: str
    user_request: str
    intake_notes: str
    evidence: list[str]
    risk_level: str
    approved: bool | None
    reviewer: str
    note: str
    action_result: str
    user_message: str
    decision: str  # auto_pass | approved | rejected | waiting_human
    path: list[str]
    role_handoff: list[str]  # 角色名轨迹（给小白看「谁接力了」）


def _append(state: WFState, key: str, item: str) -> list[str]:
    return list(state.get(key) or []) + [item]


def _append_path(state: WFState, name: str) -> list[str]:
    return _append(state, "path", name)


# ----- 角色节点 -----


def intake_role(state: WFState) -> dict[str, Any]:
    """角色·受理：登记诉求，不查系统。"""
    req = (state.get("user_request") or "").strip()
    notes = f"已受理 case={state.get('case_id')}; 诉求摘要={req[:80]}"
    return {
        "intake_notes": notes,
        "path": _append_path(state, "intake"),
        "role_handoff": _append(state, "role_handoff", "受理员"),
    }


def gather_evidence_role(state: WFState) -> dict[str, Any]:
    """角色·核查：收集证据（订单 mock + 可选政策检索）。

    【可替换】order API / 真实 Retriever。
    """
    req = state.get("user_request") or ""
    evidence = ["order_status=delivered"]  # mock 订单
    # 政策：能命中就记一条；命不中也不编造
    try:
        obs = str(search_knowledge.invoke({"query": req or "退货"}))
        if obs != "not_found" and not obs.startswith("error"):
            evidence.append(f"policy_hit={obs[:120]}")
        else:
            evidence.append("policy=7_day_unopened(mock_default)")
    except Exception as exc:  # noqa: BLE001
        evidence.append(f"policy_error={type(exc).__name__}")
    return {
        "evidence": evidence,
        "path": _append_path(state, "gather_evidence"),
        "role_handoff": _append(state, "role_handoff", "核查员"),
    }


def assess_risk_role(state: WFState) -> dict[str, Any]:
    """角色·计险：规则打 risk_level（可换成模型，但要可测）。"""
    req = state.get("user_request") or ""
    if any(k in req for k in ("破损", "投诉", "全额", "律师", "曝光")):
        risk: Risk = "high"
    elif any(k in req for k in ("质量", "少件", "差价")):
        risk = "medium"
    else:
        risk = "low"
    # medium 本课也走 HITL，简化成 high 门禁
    if risk == "medium":
        risk = "high"
    return {
        "risk_level": risk,
        "path": _append_path(state, "assess_risk"),
        "role_handoff": _append(state, "role_handoff", "风控员"),
    }


def human_review_role(state: WFState) -> dict[str, Any]:
    """角色·审核（HITL）：interrupt 等人；resume 带 approved。"""
    payload = {
        "case_id": state.get("case_id"),
        "summary": state.get("intake_notes"),
        "evidence": state.get("evidence"),
        "risk_level": state.get("risk_level"),
        "question": "高风险退货，是否批准执行？",
    }
    decision = interrupt(payload)
    if not isinstance(decision, dict):
        decision = {"approved": bool(decision), "reviewer": "?", "note": ""}
    approved = bool(decision.get("approved"))
    return {
        "approved": approved,
        "reviewer": str(decision.get("reviewer") or ""),
        "note": str(decision.get("note") or ""),
        "decision": "approved" if approved else "rejected",
        "path": _append_path(state, "human_review"),
        "role_handoff": _append(state, "role_handoff", "审核员"),
    }


def execute_or_skip_role(state: WFState) -> dict[str, Any]:
    """角色·执行：低风险自动过；批准后 mock 开单；驳回则记 rejected。"""
    risk = state.get("risk_level") or "low"
    approved = state.get("approved")

    if risk == "low":
        return {
            "action_result": "mock_return_created",
            "decision": "auto_pass",
            "path": _append_path(state, "execute_or_skip"),
            "role_handoff": _append(state, "role_handoff", "执行员"),
        }
    if approved is True:
        return {
            "action_result": "mock_return_created",
            "decision": "approved",
            "path": _append_path(state, "execute_or_skip"),
            "role_handoff": _append(state, "role_handoff", "执行员"),
        }
    if approved is False:
        return {
            "action_result": "rejected",
            "decision": "rejected",
            "path": _append_path(state, "execute_or_skip"),
            "role_handoff": _append(state, "role_handoff", "执行员"),
        }
    return {
        "action_result": "WAITING_HUMAN",
        "decision": "waiting_human",
        "path": _append_path(state, "execute_or_skip"),
        "role_handoff": _append(state, "role_handoff", "执行员"),
    }


def draft_reply_role(state: WFState) -> dict[str, Any]:
    """角色·话术：只基于 State 证据写用户消息，禁止编造未写入事实。"""
    evidence = state.get("evidence") or []
    ev_txt = "; ".join(evidence)
    action = state.get("action_result") or ""
    if action == "WAITING_HUMAN":
        msg = f"已生成审核摘要，等待人工确认。证据：{ev_txt}"
    elif action == "rejected":
        msg = f"审核未通过，未创建退货单。已参考证据：{ev_txt}"
    else:
        msg = (
            f"已根据证据处理。结果={action}。"
            f"证据={ev_txt}。"
            f"（decision={state.get('decision')}）"
        )
    return {
        "user_message": msg,
        "path": _append_path(state, "draft_reply"),
        "role_handoff": _append(state, "role_handoff", "话术员"),
    }


# ----- 路由 -----


def after_assess(state: WFState) -> Literal["human_review", "execute_or_skip"]:
    """风控门禁：高风险进人工，否则自动执行。"""
    return "human_review" if state.get("risk_level") == "high" else "execute_or_skip"


def build_workflow(*, fresh_memory: bool = True):
    """编译工作流图。"""
    g = StateGraph(WFState)
    g.add_node("intake", intake_role)
    g.add_node("gather_evidence", gather_evidence_role)
    g.add_node("assess_risk", assess_risk_role)
    g.add_node("human_review", human_review_role)
    g.add_node("execute_or_skip", execute_or_skip_role)
    g.add_node("draft_reply", draft_reply_role)

    g.add_edge(START, "intake")
    g.add_edge("intake", "gather_evidence")
    g.add_edge("gather_evidence", "assess_risk")
    g.add_conditional_edges(
        "assess_risk",
        after_assess,
        {
            "human_review": "human_review",
            "execute_or_skip": "execute_or_skip",
        },
    )
    g.add_edge("human_review", "execute_or_skip")
    g.add_edge("execute_or_skip", "draft_reply")
    g.add_edge("draft_reply", END)

    saver = MemorySaver()
    return g.compile(checkpointer=saver), saver


def thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def _blank(case_id: str, user_request: str) -> WFState:
    return {
        "case_id": case_id,
        "user_request": user_request,
        "intake_notes": "",
        "evidence": [],
        "risk_level": "",
        "approved": None,
        "reviewer": "",
        "note": "",
        "action_result": "",
        "user_message": "",
        "decision": "",
        "path": [],
        "role_handoff": [],
    }


def structured_result(state: dict[str, Any]) -> dict[str, Any]:
    """BFF/工单系统友好的结构化输出。"""
    return {
        "case_id": state.get("case_id"),
        "decision": state.get("decision"),
        "risk_level": state.get("risk_level"),
        "action_result": state.get("action_result"),
        "user_message": state.get("user_message"),
        "evidence": list(state.get("evidence") or []),
        "role_handoff": list(state.get("role_handoff") or []),
        "path": list(state.get("path") or []),
    }


def run_low_risk(
    user_request: str = "七天无理由退货",
    *,
    case_id: str = "R-1",
    thread_id: str = "wf-low-1",
) -> dict[str, Any]:
    """低风险：无人审批，直达 user_message。"""
    app, _ = build_workflow()
    cfg = thread_config(thread_id)
    out = app.invoke(_blank(case_id, user_request), cfg)
    snap = app.get_state(cfg)
    return {
        "values": dict(snap.values),
        "structured": structured_result(out),
        "interrupted": bool(getattr(snap, "interrupts", None)),
    }


def run_high_risk_pause(
    user_request: str = "破损要全额退款",
    *,
    case_id: str = "R-2",
    thread_id: str = "wf-high-1",
    app=None,
) -> dict[str, Any]:
    """高风险：停在 human_review。"""
    if app is None:
        app, _ = build_workflow()
    cfg = thread_config(thread_id)
    out = app.invoke(_blank(case_id, user_request), cfg)
    snap = app.get_state(cfg)
    return {
        "app": app,
        "config": cfg,
        "output": out,
        "values": dict(snap.values),
        "next": tuple(snap.next or ()),
        "interrupted": bool(getattr(snap, "interrupts", None) or out.get("__interrupt__")),
        "structured": structured_result(dict(snap.values)),
    }


def resume_high_risk(
    app,
    thread_id: str,
    *,
    approved: bool,
    reviewer: str = "ops_01",
    note: str = "",
) -> dict[str, Any]:
    """高风险 resume。"""
    cfg = thread_config(thread_id)
    out = app.invoke(
        Command(
            resume={"approved": approved, "reviewer": reviewer, "note": note}
        ),
        cfg,
    )
    return {"values": out, "structured": structured_result(out)}


if __name__ == "__main__":
    print("LOW", run_low_risk()["structured"])
    paused = run_high_risk_pause()
    print("HIGH wait", paused["next"], paused["interrupted"])
    print(
        "HIGH ok",
        resume_high_risk(paused["app"], "wf-high-1", approved=True)["structured"],
    )
