# app/api/cs.py
"""课次 11.02 · 对话客服 HTTP：POST /v1/cs/chat。

须带内部头；响应含 action=reply|handoff，handoff 时 summary 非空。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.lessons.m11_02_cs_integration import run_cs_turn
from app.security.internal_auth import InternalContext, require_internal_context

router = APIRouter(prefix="/v1", tags=["cs"])
logger = logging.getLogger("ai-service.cs")


class CsChatIn(BaseModel):
    """客服入参。"""

    message: str = Field(..., description="用户消息")
    session_id: str = Field(default="s1", description="会话 id（多轮记忆键）")


class CsChatOut(BaseModel):
    """客服出参：自动答或转人工。"""

    ok: bool
    action: str = Field(description="reply | handoff | error")
    reply: str
    reason: str = ""
    summary: str = ""
    session_id: str
    tenant_id: str
    trace: list[dict[str, Any]] = Field(default_factory=list)
    session_tracking: str = ""


@router.post("/cs/chat", response_model=CsChatOut)
def cs_chat(
    body: CsChatIn,
    ctx: InternalContext = Depends(require_internal_context),
) -> CsChatOut:
    """对话客服一轮：FAQ 自动答或 handoff。"""
    logger.info(
        "cs_chat tenant=%s session=%s action_pending",
        ctx.tenant_id,
        body.session_id,
    )
    out = run_cs_turn(
        body.message,
        tenant_id=ctx.tenant_id,
        session_id=body.session_id or "s1",
    )
    return CsChatOut(
        ok=bool(out.get("ok")),
        action=str(out.get("action") or "reply"),
        reply=str(out.get("reply") or ""),
        reason=str(out.get("reason") or ""),
        summary=str(out.get("summary") or ""),
        session_id=str(out.get("session_id") or body.session_id),
        tenant_id=str(out.get("tenant_id") or ctx.tenant_id),
        trace=list(out.get("trace") or []),
        session_tracking=str(out.get("session_tracking") or ""),
    )
