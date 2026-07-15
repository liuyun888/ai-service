# app/graphs/hitl.py
"""课次 07.06 · 图内 HITL：interrupt 暂停 → 人工批准/驳回 → resume。

拓扑：
  START → validate_order → prepare_summary → human_review
        → (approved?) execute_refund | reject_notify → END

安全铁律：
- prepare_summary 只生成「拟退货摘要」，绝不调退款写入
- execute_refund 仅在人工 approved=True 之后可达

依赖：Checkpointer（同 thread_id 才能跨请求 resume）。
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class HITLState(TypedDict, total=False):
    """退货审核图状态。

    order_id: 订单号
    order_ok: 校验是否通过
    summary: 拟退货摘要（给人看，不是已执行）
    approved: 人工结论；暂停期间可为空
    reviewer: 审批人
    note: 审批备注
    result: 最终结果码/话术
    executed_write: 是否真正走过写入节点（验收用）
    path: 节点轨迹
    """

    order_id: str
    order_ok: bool
    summary: str
    approved: bool | None
    reviewer: str
    note: str
    result: str
    executed_write: bool
    path: list[str]


def _append_path(state: HITLState, name: str) -> list[str]:
    return list(state.get("path") or []) + [name]


def validate_order(state: HITLState) -> dict[str, Any]:
    """校验订单：教学规则——以 ORD 开头且非 UNKNOWN 视为通过。"""
    oid = (state.get("order_id") or "").strip().upper()
    ok = bool(oid.startswith("ORD") and "UNKNOWN" not in oid)
    return {
        "order_id": oid or "ORD-UNKNOWN",
        "order_ok": ok,
        "executed_write": False,
        "path": _append_path(state, "validate_order"),
    }


def prepare_summary(state: HITLState) -> dict[str, Any]:
    """只准备给人工看的摘要——此处禁止任何退款/改库副作用。"""
    oid = state.get("order_id") or ""
    if not state.get("order_ok"):
        summary = f"订单 {oid} 校验未通过，建议驳回或让用户重填。"
    else:
        summary = f"拟对订单 {oid} 执行退货退款（mock 摘要，尚未执行任何写入）。"
    return {
        "summary": summary,
        "result": "READY_FOR_HUMAN",
        "path": _append_path(state, "prepare_summary"),
    }


def human_review(state: HITLState) -> dict[str, Any]:
    """人工确认点：调用 interrupt，把待审载荷抛给外部，图在此暂停。

    resume 时传入的 dict 会成为 interrupt() 的返回值。
    期望形如：{"approved": true, "reviewer": "ops_01", "note": "同意"}
    """
    payload = {
        "question": "是否批准执行退货写入？",
        "order_id": state.get("order_id"),
        "summary": state.get("summary"),
        "order_ok": state.get("order_ok"),
    }
    decision = interrupt(payload)
    # decision 可能是 dict；容错非 dict
    if not isinstance(decision, dict):
        decision = {"approved": bool(decision), "reviewer": "unknown", "note": ""}
    approved = bool(decision.get("approved"))
    return {
        "approved": approved,
        "reviewer": str(decision.get("reviewer") or ""),
        "note": str(decision.get("note") or ""),
        "path": _append_path(state, "human_review"),
    }


def execute_refund(state: HITLState) -> dict[str, Any]:
    """写入节点：仅审批通过后可达（mock，不接真实支付）。"""
    oid = state.get("order_id")
    reviewer = state.get("reviewer") or "?"
    return {
        "result": f"已执行退货处理（mock）order={oid}; by={reviewer}",
        "executed_write": True,
        "path": _append_path(state, "execute_refund"),
    }


def reject_notify(state: HITLState) -> dict[str, Any]:
    """驳回：明确告知用户，绝不静默、绝不执行写入。"""
    return {
        "result": "已驳回，未执行任何写入",
        "executed_write": False,
        "path": _append_path(state, "reject_notify"),
    }


def route_after_human(state: HITLState) -> Literal["execute_refund", "reject_notify"]:
    """批准 → 写入；否则驳回通知。"""
    if state.get("approved"):
        return "execute_refund"
    return "reject_notify"


def build_hitl_graph(*, fresh_memory: bool = False):
    """编译 HITL 图（必须带 checkpointer，否则 interrupt 无法跨 invoke 恢复）。"""
    g = StateGraph(HITLState)
    g.add_node("validate_order", validate_order)
    g.add_node("prepare_summary", prepare_summary)
    g.add_node("human_review", human_review)
    g.add_node("execute_refund", execute_refund)
    g.add_node("reject_notify", reject_notify)

    g.add_edge(START, "validate_order")
    g.add_edge("validate_order", "prepare_summary")
    g.add_edge("prepare_summary", "human_review")
    g.add_conditional_edges(
        "human_review",
        route_after_human,
        {
            "execute_refund": "execute_refund",
            "reject_notify": "reject_notify",
        },
    )
    g.add_edge("execute_refund", END)
    g.add_edge("reject_notify", END)

    saver = MemorySaver()
    return g.compile(checkpointer=saver), saver


def thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def start_review(order_id: str, thread_id: str, *, app=None) -> dict[str, Any]:
    """第一次 invoke：跑到 human_review 暂停。"""
    if app is None:
        app, _ = build_hitl_graph()
    cfg = thread_config(thread_id)
    out = app.invoke(
        {
            "order_id": order_id,
            "order_ok": False,
            "summary": "",
            "approved": None,
            "reviewer": "",
            "note": "",
            "result": "",
            "executed_write": False,
            "path": [],
        },
        cfg,
    )
    snap = app.get_state(cfg)
    interrupted = bool(getattr(snap, "interrupts", None) or out.get("__interrupt__"))
    return {
        "app": app,
        "config": cfg,
        "output": out,
        "values": dict(snap.values),
        "next": tuple(snap.next or ()),
        "interrupted": interrupted,
        "interrupt_value": (
            snap.interrupts[0].value
            if getattr(snap, "interrupts", None)
            else None
        ),
    }


def resume_review(
    app,
    thread_id: str,
    *,
    approved: bool,
    reviewer: str = "ops_01",
    note: str = "",
) -> dict[str, Any]:
    """人工提交后 resume：同一 thread_id + Command(resume=...)。"""
    cfg = thread_config(thread_id)
    out = app.invoke(
        Command(
            resume={
                "approved": approved,
                "reviewer": reviewer,
                "note": note,
            }
        ),
        cfg,
    )
    snap = app.get_state(cfg)
    return {
        "output": out,
        "values": dict(snap.values),
        "next": tuple(snap.next or ()),
    }


if __name__ == "__main__":
    app, _ = build_hitl_graph()
    tid = "return-1"
    paused = start_review("ORD-A100", tid, app=app)
    print("paused", paused["interrupted"], paused["values"].get("result"))
    print("resume", resume_review(app, tid, approved=True)["values"])
