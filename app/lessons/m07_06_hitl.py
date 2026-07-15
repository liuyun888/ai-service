# app/lessons/m07_06_hitl.py
"""课次 07.06 · HITL 包装：暂停 / 批准 / 驳回三条验收路径。"""

from __future__ import annotations

from typing import Any

from app.graphs.hitl import build_hitl_graph, resume_review, start_review


def demo_pause_then_approve() -> dict[str, Any]:
    """暂停 → 批准 → execute_refund，且 executed_write=True。"""
    app, _ = build_hitl_graph()
    tid = "hitl-approve-1"
    paused = start_review("ORD-A100", tid, app=app)
    done = resume_review(
        app, tid, approved=True, reviewer="ops_01", note="同意退货"
    )
    return {"paused": paused, "done": done}


def demo_pause_then_reject() -> dict[str, Any]:
    """暂停 → 驳回 → reject_notify，executed_write 必须为 False。"""
    app, _ = build_hitl_graph()
    tid = "hitl-reject-1"
    paused = start_review("ORD-B200", tid, app=app)
    done = resume_review(
        app, tid, approved=False, reviewer="ops_02", note="材料不全"
    )
    return {"paused": paused, "done": done}


def demo_no_execute_while_waiting() -> dict[str, Any]:
    """未 resume 前：next 停在 human_review，不得出现 execute_refund。"""
    app, _ = build_hitl_graph()
    tid = "hitl-wait-1"
    paused = start_review("ORD-C300", tid, app=app)
    path = paused["values"].get("path") or []
    return {
        "paused": paused,
        "path": path,
        "has_execute": "execute_refund" in path,
    }


def bff_contract_notes() -> list[str]:
    """前后端契约（写进笔记）。"""
    return [
        "第一次响应：status=interrupted + thread_id + summary 摘要",
        "人工在工单台批准/驳回",
        "BFF 用同一 thread_id 调 resume（Command(resume=...)）",
        "写入类 Tool 只能在 approved 之后的节点",
    ]
