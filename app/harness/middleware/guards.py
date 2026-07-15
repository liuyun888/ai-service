# app/harness/middleware/guards.py
"""课次 08.06 · 合规护栏中间件（CommitmentGuard）。

在 before_final 钩子拦截绝对承诺；高置信规则直接改写，其余可进审核队列。
"""

from __future__ import annotations

import re
from typing import Any

# 可调：命中则拦截。放宽正则 → 漏拦风险上升；收紧 → 误杀上升。
ABSOLUTE = re.compile(r"(保证|一定|百分百).{0,12}(到货|送达|治愈|赚钱|退款)")

SAFE_REWRITE = (
    "我无法做出绝对承诺。请以订单页时效/书面政策为准，我可以帮你查询当前状态。"
)


def commitment_guard(text: str) -> tuple[bool, str]:
    """检查即将发出的回复是否含绝对承诺。

    参数:
        text: 模型草稿回复

    返回:
        (ok, text)：ok=False 表示已拦截并改写
    """
    raw = text or ""
    if ABSOLUTE.search(raw):
        return False, SAFE_REWRITE
    return True, raw


def commitment_guard_event(text: str) -> dict[str, Any]:
    """带 Trace 字段的护栏结果（给中间件链用）。"""
    ok, out = commitment_guard(text)
    return {
        "hook": "before_final",
        "middleware": "CommitmentGuard",
        "triggered": not ok,
        "rule": "absolute_promise" if not ok else "",
        "input_preview": raw_preview(text),
        "output": out,
        "ok": ok,
    }


def raw_preview(text: str, n: int = 80) -> str:
    t = (text or "").replace("\n", " ")
    return t if len(t) <= n else t[: n - 1] + "…"
