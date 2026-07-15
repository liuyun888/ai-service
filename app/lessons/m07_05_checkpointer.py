# app/lessons/m07_05_checkpointer.py
"""课次 07.05 · Checkpointer 包装：同线程续跑 / 异线程隔离 / 反例覆盖。"""

from __future__ import annotations

from typing import Any

from app.graphs.checkpointing import (
    build_cp_graph,
    get_values,
    run_first,
    run_resume,
    run_wrong_overwrite,
)


def demo_same_thread_resume() -> dict[str, Any]:
    """同 thread_id：第一枪 count=1，续跑 count=2，log 变长。"""
    app, saver = build_cp_graph(fresh_memory=True)
    tid = "case-10086"
    first = run_first(tid, app=app)
    second = run_resume(app, tid)
    return {
        "thread_id": tid,
        "first": first["values"],
        "second": second["values"],
        "saver_type": type(saver).__name__,
    }


def demo_isolation() -> dict[str, Any]:
    """不同 thread_id：互不污染。"""
    app, _ = build_cp_graph(fresh_memory=True)
    a = run_first("tenantA-case-1", app=app)
    # A 再续一次 → count=2
    run_resume(app, "tenantA-case-1")
    b = run_first("tenantB-case-1", app=app)
    return {
        "A_after_resume": get_values(app, "tenantA-case-1"),
        "B_fresh": b["values"],
        "lesson": "猜不到/鉴权住 thread_id，才能防跨租户续跑",
    }


def demo_overwrite_trap() -> dict[str, Any]:
    """演示错误续跑：再次传入 count=0。"""
    app, _ = build_cp_graph(fresh_memory=True)
    tid = "trap-1"
    run_first(tid, app=app)
    run_resume(app, tid)  # count=2
    wrong = run_wrong_overwrite(app, tid)
    right = run_resume(app, tid)
    return {
        "after_resume_before_trap": 2,
        "after_wrong_invoke_count0": wrong["values"],
        "after_correct_empty_resume": right["values"],
        "lesson": wrong["lesson"],
    }


def production_checklist() -> list[str]:
    """笔记里必写的生产要求。"""
    return [
        "MemorySaver 仅开发：进程内、重启丢、多副本不共享",
        "生产换 Postgres/Redis 等官方或社区 Checkpointer",
        "thread_id 不可预测，并在 BFF 校验租户归属",
        "敏感字段进 State 前脱敏或外置",
        "聊天记忆 ≠ Checkpoint：后者存整图位置，丢了可能无法续跑",
    ]
