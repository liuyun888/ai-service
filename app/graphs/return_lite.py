# app/graphs/return_intake_lite.py
"""课次 07.01 · 最小「退货受理」状态图（对照单 Agent）。

故意做得很瘦：演示「阶段钉死在边上」，不是完整生产审批流。
完整 HITL 暂停 / Checkpointer 留给 07.05–07.06。

路径：
  classify → faq_answer → END
           → validate_order → await_human → draft_ticket → END
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.tools.knowledge import search_knowledge


class ReturnLiteState(TypedDict, total=False):
    """退货轻量图的共享状态（字段含义写给人看）。"""

    user_text: str  # 用户原话
    intent: str  # faq | return | other
    order_id: str  # 从话术抠出的订单号（演示）
    order_ok: bool  # 订单是否通过校验
    needs_human: bool  # 是否需要人工确认（退货路径恒为 True）
    answer: str  # 最终回复
    path: list[str]  # 走过的节点名（可观测）


def _append_path(state: ReturnLiteState, name: str) -> list[str]:
    """追加路径：每个节点自己带上完整 path（本课未上 reducer）。"""
    return list(state.get("path") or []) + [name]


def classify_node(state: ReturnLiteState) -> dict[str, Any]:
    """入口分类：FAQ 口语 vs 退货诉求（规则版，不调 Chat）。"""
    text = state.get("user_text") or ""
    if any(k in text for k in ("退货", "退款", "退换")):
        intent: Literal["faq", "return", "other"] = "return"
    elif any(k in text for k in ("尺寸", "包装", "多大", "几天", "质保", "政策")):
        intent = "faq"
    else:
        intent = "other"
    return {"intent": intent, "path": _append_path(state, "classify")}


def faq_answer_node(state: ReturnLiteState) -> dict[str, Any]:
    """FAQ 分支：直接检索政策/须知——演示「这种其实单 Agent 也够」。"""
    obs = str(search_knowledge.invoke({"query": state.get("user_text") or ""}))
    if obs == "not_found":
        answer = "未命中知识库。请换个问法，或走人工。"
    else:
        answer = f"（FAQ 短链路）{obs}"
    return {
        "answer": answer,
        "needs_human": False,
        "path": _append_path(state, "faq_answer"),
    }


def validate_order_node(state: ReturnLiteState) -> dict[str, Any]:
    """退货分支·校验订单：mock 规则——含 ORD 字样算有效。"""
    text = state.get("user_text") or ""
    order_id = ""
    for tok in text.replace("，", " ").replace(",", " ").split():
        if tok.upper().startswith("ORD"):
            order_id = tok.upper()
            break
    if not order_id:
        order_id = "ORD-UNKNOWN"
    order_ok = order_id.startswith("ORD") and order_id != "ORD-UNKNOWN"
    return {
        "order_id": order_id,
        "order_ok": order_ok,
        "path": _append_path(state, "validate_order"),
    }


def await_human_node(state: ReturnLiteState) -> dict[str, Any]:
    """退货分支·HITL 占位：本课只标记「必须等人」，不真 pause（07.06 再 interrupt）。"""
    note = (
        f"订单 {state.get('order_id')} 校验="
        f"{'通过' if state.get('order_ok') else '未分类到有效单号'}；"
        "已暂停，待人工确认责权后再开单。"
    )
    return {
        "needs_human": True,
        "answer": note,
        "path": _append_path(state, "await_human"),
    }


def draft_ticket_node(state: ReturnLiteState) -> dict[str, Any]:
    """退货分支·开单草稿：人工确认后才会到这里（本课线性走完示意）。"""
    prev = state.get("answer") or ""
    ticket = f"TICKET-DRAFT:{state.get('order_id') or 'N/A'}"
    answer = f"{prev} → 已生成草稿 {ticket}（未真正退款）。"
    return {"answer": answer, "path": _append_path(state, "draft_ticket")}


def other_node(state: ReturnLiteState) -> dict[str, Any]:
    """兜底：不该硬塞进退货流。"""
    return {
        "answer": "暂无法归类为 FAQ 或退货。请说明包装问题或提供订单号申请退货。",
        "needs_human": False,
        "path": _append_path(state, "other"),
    }


def route_after_classify(state: ReturnLiteState) -> str:
    """条件边：按 intent 分流（写在代码里，不靠 Prompt 碰运气）。"""
    intent = state.get("intent") or "other"
    if intent == "faq":
        return "faq_answer"
    if intent == "return":
        return "validate_order"
    return "other"


def build_return_intake_graph():
    """编译退货轻量图。"""
    g = StateGraph(ReturnLiteState)
    g.add_node("classify", classify_node)
    g.add_node("faq_answer", faq_answer_node)
    g.add_node("validate_order", validate_order_node)
    g.add_node("await_human", await_human_node)
    g.add_node("draft_ticket", draft_ticket_node)
    g.add_node("other", other_node)

    g.add_edge(START, "classify")
    g.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "faq_answer": "faq_answer",
            "validate_order": "validate_order",
            "other": "other",
        },
    )
    g.add_edge("faq_answer", END)
    g.add_edge("validate_order", "await_human")
    g.add_edge("await_human", "draft_ticket")
    g.add_edge("draft_ticket", END)
    g.add_edge("other", END)
    return g.compile()


def run_return_lite(user_text: str) -> ReturnLiteState:
    """跑一遍轻量图，返回最终 State。"""
    app = build_return_intake_graph()
    out = app.invoke({"user_text": user_text, "path": []})
    return out  # type: ignore[return-value]
