# app/lessons/m11_03_workflow_integration.py
"""课次 11.03 · 多步工作流集成：把 M07 图接到 HTTP 可演示入口。

要点：
- case_id 即 thread_id（跨请求 resume 不丢）
- 模块级单例图 + MemorySaver（fresh_memory=False）
- public_view：decision → status（completed | waiting_human | rejected）
"""

from __future__ import annotations

from typing import Any

from langgraph.types import Command

from app.graphs.workflow import (
    _blank,
    build_workflow,
    structured_result,
    thread_config,
)
from app.harness.shell import ensure_tenant
from app.lessons.m07_07_multiagent_workflow import industry_analogs, role_catalog

# 单例：API 多请求共享同一 checkpointer，否则 resume 找不到线程
_WF_APP, _WF_SAVER = build_workflow(fresh_memory=True)


def get_workflow_app():
    """取得共享工作流应用（测试可替换，见 reset_workflow_app_for_tests）。"""
    return _WF_APP


def reset_workflow_app_for_tests() -> None:
    """测试隔离：换新 MemorySaver，避免 case_id 撞车。"""
    global _WF_APP, _WF_SAVER
    _WF_APP, _WF_SAVER = build_workflow(fresh_memory=True)


def decision_to_status(decision: str | None, *, interrupted: bool = False) -> str:
    """映射正文契约 status。"""
    if interrupted or decision in ("", None, "waiting_human"):
        if interrupted or decision == "waiting_human":
            return "waiting_human"
    d = decision or ""
    if d in ("auto_pass", "approved"):
        return "completed"
    if d == "rejected":
        return "rejected"
    if d == "waiting_human":
        return "waiting_human"
    return "waiting_human" if interrupted else (d or "unknown")


def public_view(
    state: dict[str, Any] | None,
    *,
    interrupted: bool = False,
    interrupt_payload: Any = None,
) -> dict[str, Any]:
    """工单台/BFF 友好结构（对齐正文 JSON）。"""
    st = dict(state or {})
    base = structured_result(st)
    status = decision_to_status(base.get("decision"), interrupted=interrupted)
    # 暂停时 decision 可能还空，强制 waiting_human
    if interrupted:
        status = "waiting_human"
        if not base.get("decision"):
            base["decision"] = "waiting_human"
        if not base.get("action_result"):
            base["action_result"] = "WAITING_HUMAN"
    return {
        "case_id": base.get("case_id"),
        "status": status,
        "risk_level": base.get("risk_level") or "",
        "evidence": list(base.get("evidence") or []),
        "action_result": base.get("action_result") or "",
        "user_message": base.get("user_message") or "",
        "decision": base.get("decision") or "",
        "role_handoff": list(base.get("role_handoff") or []),
        "path": list(base.get("path") or []),
        "interrupted": interrupted,
        "interrupt": interrupt_payload,
    }


def _snap_interrupt(app, cfg: dict[str, Any]) -> tuple[bool, Any]:
    snap = app.get_state(cfg)
    interrupts = getattr(snap, "interrupts", None) or ()
    interrupted = bool(interrupts) or bool(snap.next)
    payload = None
    if interrupts:
        first = interrupts[0]
        payload = getattr(first, "value", first)
    return interrupted, payload


def start_return_workflow(
    case_id: str,
    user_request: str,
    *,
    tenant_id: str = "demo",
) -> dict[str, Any]:
    """启动退货工作流；高风险会停在 HITL。"""
    ok, msg = ensure_tenant(tenant_id)
    if not ok:
        return {
            "ok": False,
            "status": "rejected",
            "case_id": case_id,
            "user_message": msg,
            "error": msg,
        }
    cid = (case_id or "").strip() or "R-unknown"
    app = get_workflow_app()
    cfg = thread_config(cid)
    out = app.invoke(_blank(cid, user_request), cfg)
    interrupted, payload = _snap_interrupt(app, cfg)
    values = dict(app.get_state(cfg).values)
    # invoke 返回可能含 __interrupt__
    if isinstance(out, dict) and out.get("__interrupt__"):
        interrupted = True
    view = public_view(values, interrupted=interrupted, interrupt_payload=payload)
    view["ok"] = True
    view["tenant_id"] = tenant_id
    return view


def resume_return_workflow(
    case_id: str,
    *,
    approved: bool,
    reviewer: str = "ops_01",
    note: str = "",
    tenant_id: str = "demo",
) -> dict[str, Any]:
    """人工审批后续跑。"""
    ok, msg = ensure_tenant(tenant_id)
    if not ok:
        return {
            "ok": False,
            "status": "rejected",
            "case_id": case_id,
            "user_message": msg,
            "error": msg,
        }
    cid = (case_id or "").strip() or "R-unknown"
    app = get_workflow_app()
    cfg = thread_config(cid)
    out = app.invoke(
        Command(
            resume={
                "approved": bool(approved),
                "reviewer": reviewer or "ops_01",
                "note": note or "",
            }
        ),
        cfg,
    )
    interrupted, payload = _snap_interrupt(app, cfg)
    values = out if isinstance(out, dict) else dict(app.get_state(cfg).values)
    # 去掉内部键
    values = {k: v for k, v in values.items() if not str(k).startswith("__")}
    view = public_view(values, interrupted=interrupted, interrupt_payload=payload)
    view["ok"] = True
    view["tenant_id"] = tenant_id
    return view


def demo_suite() -> dict[str, Any]:
    """11.03 验收：低风险自动过；高风险暂停；approve 后完成。"""
    reset_workflow_app_for_tests()

    low = start_return_workflow(
        "R-low-1103",
        "七天无理由退货，未拆封",
        tenant_id="demo",
    )
    high = start_return_workflow(
        "R-high-1103",
        "破损要全额退款",
        tenant_id="demo",
    )
    resumed = resume_return_workflow(
        "R-high-1103",
        approved=True,
        reviewer="ops_01",
        note="同意开退货单",
        tenant_id="demo",
    )
    rejected_start = start_return_workflow(
        "R-rej-1103",
        "破损要全额并投诉",
        tenant_id="demo",
    )
    rejected = resume_return_workflow(
        "R-rej-1103",
        approved=False,
        reviewer="ops_02",
        note="材料不足",
        tenant_id="demo",
    )

    ok = (
        low.get("status") == "completed"
        and low.get("action_result") == "mock_return_created"
        and low.get("risk_level") == "low"
        and bool(low.get("evidence"))
        and high.get("status") == "waiting_human"
        and high.get("risk_level") == "high"
        and resumed.get("status") == "completed"
        and resumed.get("action_result") == "mock_return_created"
        and rejected.get("status") == "rejected"
    )
    return {
        "roles": role_catalog(),
        "analogs": industry_analogs(),
        "low": low,
        "high_pause": high,
        "high_approve": resumed,
        "high_reject": rejected,
        "rejected_start": rejected_start,
        "ok": ok,
    }
