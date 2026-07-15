# app/lessons/m07_04_conditional_routing.py
"""课次 07.04 · 条件路由包装：意图分类单测 + 三路对照。"""

from __future__ import annotations

from typing import Any

from app.graphs.router import (
    classify_intent,
    route_after_classify,
    run_router,
)


def unit_route_table() -> list[dict[str, str]]:
    """不依赖网络的路由真值表（验收用）。"""
    cases = [
        ("这款鞋防水吗", "product", "retrieve"),
        ("耳机质保多久", "product", "retrieve"),
        ("订单 10086 到哪了", "order", "order_tool"),
        ("运单 SF123456 到哪了", "order", "order_tool"),
        ("你好", "other", "clarify"),
        ("今天心情怎么样", "other", "clarify"),
    ]
    rows: list[dict[str, str]] = []
    for query, expect_intent, expect_route in cases:
        intent = classify_intent(query)
        route = route_after_classify({"intent": intent, "query": query})  # type: ignore[arg-type]
        rows.append(
            {
                "query": query,
                "intent": intent,
                "route": route,
                "expect_intent": expect_intent,
                "expect_route": expect_route,
                "ok": str(intent == expect_intent and route == expect_route),
            }
        )
    return rows


def demo_three_branches() -> dict[str, Any]:
    """三种输入 → 不同 path / answer 前缀。"""
    product = run_router("退货几天内可以？")
    order = run_router("订单 10086 到哪了")
    other = run_router("你好")
    return {"product": product, "order": order, "other": other}


def illegal_intent_fallback() -> str:
    """非法 intent 必须澄清。"""
    return route_after_classify({"intent": "hack_refund", "query": "x"})  # type: ignore[arg-type]
