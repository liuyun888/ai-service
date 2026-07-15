# app/lessons/m08_02_five_dimensions.py
"""课次 08.02 · 五维工程模型包装：长工单巡检 + 专栏对照。"""

from __future__ import annotations

from typing import Any

from app.harness.five_dimensions import (
    DIMENSIONS,
    ordered_checkup,
    profile_column_stack,
    profile_faq,
    profile_long_ticket_bare,
    rows_as_table,
    why_long_task_harder,
)


def demo_suite() -> dict[str, Any]:
    long_bare = profile_long_ticket_bare()
    faq = profile_faq()
    column = profile_column_stack()
    return {
        "dimensions": DIMENSIONS,
        "long_bare": long_bare,
        "faq": faq,
        "column": column,
        "long_gaps": rows_as_table(long_bare),
        "checkup_order": ordered_checkup(long_bare),
        "why_long": why_long_task_harder(),
    }
