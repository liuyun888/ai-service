# app/graphs/router.py
"""课次 07.04 · 条件路由：按 intent 分流（可单测的路由函数）。

拓扑：
  START → classify ─┬─ product → retrieve  → generate → END
                    ├─ order   → order_tool → generate → END
                    └─ other   → clarify → END

要点：
- route_after_classify 返回的是「节点名」，不是中文展示文案
- intent 写入 State，方便 Trace
- unknown / 非法 intent → 一律澄清（安全默认）
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.tools.inventory import get_shipment
from app.tools.knowledge import search_knowledge

Intent = Literal["product", "order", "other"]
RouteName = Literal["retrieve", "order_tool", "clarify"]


class RouterState(TypedDict, total=False):
    """条件路由图状态。

    query: 用户原话
    intent: product | order | other（分类结果，必写回便于日志）
    docs: 商品/政策检索片段
    tool_obs: 订单/运单 Tool 观察
    answer: 最终回复
    path: 走过的节点
    """

    query: str
    intent: str
    docs: list[str]
    tool_obs: str
    answer: str
    path: list[str]


def _append_path(state: RouterState, name: str) -> list[str]:
    return list(state.get("path") or []) + [name]


def classify_intent(query: str) -> Intent:
    """纯函数分类：不依赖网络，方便单测。

    规则够粗：演示「意图 → 路径」；生产可换成小模型，但请保持本接口。
    """
    q = query or ""
    # 订单/物流优先（避免「退货订单」歧义时先走业务状态）
    if any(k in q for k in ("订单", "物流", "快递", "运单", "到哪", "SF", "YT")):
        return "order"
    if any(k in q for k in ("规格", "参数", "防水", "尺寸", "材料", "退货", "质保", "政策")):
        return "product"
    return "other"


def classify(state: RouterState) -> dict[str, Any]:
    """节点：写入 intent。"""
    intent = classify_intent(state.get("query") or "")
    return {"intent": intent, "path": _append_path(state, "classify")}


def retrieve(state: RouterState) -> dict[str, Any]:
    """商品/政策分支：检索（可替换为向量库）。"""
    query = state.get("query") or ""
    obs = str(search_knowledge.invoke({"query": query}))
    if obs == "not_found" or obs.startswith("error"):
        docs = [f"[检索空] 未命中「{query}」相关资料"]
    else:
        docs = [p.strip() for p in obs.split(" | ") if p.strip()]
    return {"docs": docs, "path": _append_path(state, "retrieve")}


def order_tool(state: RouterState) -> dict[str, Any]:
    """订单分支：调运单 Tool（mock）；无运单号时写明需补充。"""
    query = state.get("query") or ""
    tracking = ""
    for tok in query.replace("，", " ").replace(",", " ").split():
        up = tok.strip().upper()
        if up.startswith(("SF", "YT")) and any(c.isdigit() for c in up):
            tracking = up
            break
    if not tracking:
        # 演示：用户说「订单 10086」时用占位，真实应查订单号→运单映射
        if "10086" in query:
            tracking = "SF123456"
        else:
            obs = "error: 未解析到运单号；请提供 SF/YT 运单或完整订单号"
            return {"tool_obs": obs, "path": _append_path(state, "order_tool")}
    obs = str(get_shipment.invoke({"tracking_no": tracking}))
    return {"tool_obs": obs, "path": _append_path(state, "order_tool")}


def clarify(state: RouterState) -> dict[str, Any]:
    """兜底：澄清，不乱调写入 Tool。"""
    return {
        "answer": "请说明是商品/政策咨询，还是订单/物流查询？（可带规格关键词或运单号）",
        "path": _append_path(state, "clarify"),
    }


def generate(state: RouterState) -> dict[str, Any]:
    """商品/订单两路汇合后的生成（读不同中间字段）。"""
    intent = state.get("intent") or ""
    if intent == "product":
        docs = state.get("docs") or []
        body = " | ".join(docs) if docs else "（无资料）"
        answer = f"[检索] {body}"
    elif intent == "order":
        answer = f"[Tool] {state.get('tool_obs') or '（无观察）'}"
    else:
        answer = state.get("answer") or "请补充问题类型。"
    return {"answer": answer, "path": _append_path(state, "generate")}


def route_after_classify(state: RouterState) -> RouteName:
    """条件边路由函数：返回下一节点名（可单测）。

    非法 / 缺失 intent → clarify（安全默认）。
    """
    mapping: dict[str, RouteName] = {
        "product": "retrieve",
        "order": "order_tool",
        "other": "clarify",
    }
    intent = state.get("intent") or "other"
    return mapping.get(intent, "clarify")


def build_router_graph():
    """编译路由图。"""
    g = StateGraph(RouterState)
    g.add_node("classify", classify)
    g.add_node("retrieve", retrieve)
    g.add_node("order_tool", order_tool)
    g.add_node("clarify", clarify)
    g.add_node("generate", generate)

    g.add_edge(START, "classify")
    g.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "retrieve": "retrieve",
            "order_tool": "order_tool",
            "clarify": "clarify",
        },
    )
    g.add_edge("retrieve", "generate")
    g.add_edge("order_tool", "generate")
    g.add_edge("generate", END)
    g.add_edge("clarify", END)
    return g.compile()


def run_router(query: str) -> RouterState:
    """一键调用。"""
    app = build_router_graph()
    out = app.invoke(
        {
            "query": query,
            "intent": "",
            "docs": [],
            "tool_obs": "",
            "answer": "",
            "path": [],
        }
    )
    return out  # type: ignore[return-value]


if __name__ == "__main__":
    for q in ("这款鞋防水吗", "订单 10086 到哪了", "你好"):
        print(q, "=>", run_router(q))
