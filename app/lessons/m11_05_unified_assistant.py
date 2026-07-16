# app/lessons/m11_05_unified_assistant.py
"""课次 11.05 · 统一助手编排：把 11.01～11.04 接到一条入口。

直觉：浏览器只认「发一句话 → 流式回字」；背后按意图分流到
业务助手 / 客服 / 退货工作流 / 知识库+护栏，再统一出口。

路由优先级（可调关键词见下方常量）：
1) 投诉/转人工/物流运单 → 客服（11.02）
2) 明确申请退货工单 → 工作流 start（11.03）
3) 上传知识标记 / 诱导绝对承诺 → 知识库+护栏（11.04）
4) 默认 → 业务助手 RAG+库存（11.01）
最后：非 handoff 的回复再过一遍 CommitmentGuard，避免页面漏拦。
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.lessons.m11_01_assistant_integration import run_assistant_turn
from app.lessons.m11_02_cs_integration import check_handoff_rules, load_cs_config, run_cs_turn
from app.lessons.m11_03_workflow_integration import start_return_workflow
from app.lessons.m11_04_kb_guard_integration import (
    POLICY_MARKER,
    finalize_with_guard,
    run_kb_guard_turn,
)

# 可调：命中任一则走退货工作流（高风险话术会进 waiting_human）
WORKFLOW_KEYWORDS = (
    "申请退货工单",
    "创建退货工单",
    "启动退货",
    "破损要求全额退款",
    "破损要全额",
)

# 可调：命中则走知识库路径（需先 ingest；含护栏诱饵句）
KB_KEYWORDS = (
    POLICY_MARKER,
    "保证明天一定退款",
    "一定退款到账",
    "上传的政策",
    "知识库里",
)

# 可调：物流/订单类走客服（多轮记忆 + 查运单）
CS_SHIP_KEYS = ("到哪", "物流", "运单", "快递", "发货", "订单 SF", "我的订单")


def _wants_workflow(text: str) -> bool:
    t = text or ""
    return any(k in t for k in WORKFLOW_KEYWORDS)


def _wants_kb(text: str) -> bool:
    t = text or ""
    return any(k in t for k in KB_KEYWORDS)


def _wants_cs_ship(text: str) -> bool:
    t = text or ""
    return any(k in t for k in CS_SHIP_KEYS)


def choose_mode(message: str) -> str:
    """只根据话术选通道；返回 assistant|cs|workflow|kb。"""
    text = (message or "").strip()
    cfg = load_cs_config()
    rules = cfg.get("handoff_rules") or {}
    kws = list(rules.get("keywords") or ["投诉", "转人工"])
    should, _ = check_handoff_rules(text, keywords=kws)
    if should or _wants_cs_ship(text):
        return "cs"
    if _wants_workflow(text):
        return "workflow"
    if _wants_kb(text):
        return "kb"
    return "assistant"


def run_unified_turn(
    message: str,
    *,
    tenant_id: str = "demo",
    session_id: str = "s1",
    request_id: str = "-",
    user_id: str = "",
) -> dict[str, Any]:
    """统一跑一轮：分流 → 对应课能力 →（可选）护栏 → 标准化字段。

    返回字段（给 SSE done / 非流式调试共用）:
        ok, reply, mode, action, session_id, tenant_id,
        evidence, trace, guard_triggered, case_id, summary, elapsed_ms
    """
    t0 = time.perf_counter()
    text = (message or "").strip()
    mode = choose_mode(text)
    out: dict[str, Any] = {
        "ok": True,
        "reply": "",
        "mode": mode,
        "action": "reply",
        "session_id": session_id,
        "tenant_id": tenant_id,
        "request_id": request_id,
        "user_id": user_id,
        "evidence": {},
        "trace": [{"step": "route", "mode": mode}],
        "guard_triggered": False,
        "case_id": "",
        "summary": "",
        "elapsed_ms": 0,
    }

    if mode == "cs":
        cs = run_cs_turn(text, tenant_id=tenant_id, session_id=session_id)
        out["ok"] = bool(cs.get("ok"))
        out["reply"] = str(cs.get("reply") or "")
        out["action"] = str(cs.get("action") or "reply")
        out["summary"] = str(cs.get("summary") or "")
        out["trace"].extend(list(cs.get("trace") or []))
        out["session_id"] = str(cs.get("session_id") or session_id)
        # handoff 文案不要被承诺护栏改写坏 summary 语义
        if out["action"] != "handoff":
            guarded = finalize_with_guard(out["reply"])
            out["reply"] = str(guarded["reply"])
            out["guard_triggered"] = bool(guarded["guard_triggered"])
            out["trace"].append({"step": "commitment_guard", "triggered": out["guard_triggered"]})
        out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
        return out

    if mode == "workflow":
        case_id = f"chat-{uuid.uuid4().hex[:10]}"
        wf = start_return_workflow(
            case_id=case_id,
            user_request=text,
            tenant_id=tenant_id,
        )
        status = str(wf.get("status") or "")
        risk = str(wf.get("risk_level") or "")
        user_msg = str(wf.get("user_message") or "")
        lines = [
            f"【退货工单】已创建 case_id={case_id}，status={status}，risk={risk}。",
        ]
        if user_msg:
            lines.append(user_msg)
        if status == "waiting_human":
            lines.append("高风险已暂停，需运营在 /v1/workflows/return/resume 审批后继续。")
        elif status == "completed":
            lines.append(f"已自动办结：{wf.get('action_result') or 'ok'}。")
        out["ok"] = bool(wf.get("ok", True))
        out["reply"] = "\n".join(lines)
        out["case_id"] = case_id
        out["action"] = "workflow"
        out["evidence"] = {
            "status": status,
            "risk_level": risk,
            "evidence": list(wf.get("evidence") or []),
        }
        out["trace"].append({"step": "workflow_start", "case_id": case_id, "status": status})
        guarded = finalize_with_guard(out["reply"])
        out["reply"] = str(guarded["reply"])
        out["guard_triggered"] = bool(guarded["guard_triggered"])
        out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
        return out

    if mode == "kb":
        kb = run_kb_guard_turn(
            text,
            tenant_id=tenant_id,
            session_id=session_id,
            request_id=request_id,
        )
        out["ok"] = bool(kb.get("ok"))
        out["reply"] = str(kb.get("reply") or "")
        out["guard_triggered"] = bool(kb.get("guard_triggered"))
        out["evidence"] = dict(kb.get("evidence") or {})
        out["trace"].extend(list(kb.get("trace") or []))
        out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
        return out

    # 默认：业务助手
    assist = run_assistant_turn(
        text,
        tenant_id=tenant_id,
        session_id=session_id,
    )
    out["ok"] = bool(assist.get("ok"))
    draft = str(assist.get("reply") or "")
    guarded = finalize_with_guard(draft)
    out["reply"] = str(guarded["reply"])
    out["guard_triggered"] = bool(guarded["guard_triggered"])
    out["evidence"] = dict(assist.get("evidence") or {})
    out["trace"].extend(list(assist.get("trace") or []))
    out["trace"].append({"step": "commitment_guard", "triggered": out["guard_triggered"]})
    out["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
    return out
