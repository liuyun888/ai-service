# app/api/kb.py
"""课次 11.04 · 知识库问答 + 护栏：POST /v1/kb/chat。

检索读 ingest 共享索引（与 /rag/ingest 同源）；出口 CommitmentGuard。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.lessons.m11_04_kb_guard_integration import run_kb_guard_turn
from app.security.internal_auth import InternalContext, require_internal_context

router = APIRouter(prefix="/v1", tags=["kb-guard"])
logger = logging.getLogger("ai-service.kb")


class KbChatIn(BaseModel):
    """知识库问答入参。"""

    message: str = Field(..., description="用户问题")
    session_id: str = Field(default="s1", description="会话 id")


class KbChatOut(BaseModel):
    """含 guard_triggered，便于前端/验收观测。"""

    ok: bool
    reply: str
    session_id: str
    tenant_id: str
    request_id: str = ""
    evidence: dict
    guard_triggered: bool = False
    trace: list = Field(default_factory=list)
    decision_order: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0


@router.post("/kb/chat", response_model=KbChatOut)
def kb_chat(
    body: KbChatIn,
    ctx: InternalContext = Depends(require_internal_context),
) -> KbChatOut:
    """上传知识可问 + before_final 护栏。"""
    logger.info(
        "kb_chat tenant=%s user=%s request_id=%s",
        ctx.tenant_id,
        ctx.user_id,
        ctx.request_id,
    )
    out = run_kb_guard_turn(
        body.message,
        tenant_id=ctx.tenant_id,
        session_id=body.session_id or "s1",
        request_id=ctx.request_id,
    )
    return KbChatOut(
        ok=bool(out.get("ok")),
        reply=str(out.get("reply") or ""),
        session_id=str(out.get("session_id") or body.session_id),
        tenant_id=str(out.get("tenant_id") or ctx.tenant_id),
        request_id=str(out.get("request_id") or ctx.request_id),
        evidence=dict(out.get("evidence") or {}),
        guard_triggered=bool(out.get("guard_triggered")),
        trace=list(out.get("trace") or []),
        decision_order=list(out.get("decision_order") or []),
        elapsed_ms=int(out.get("elapsed_ms") or 0),
    )
