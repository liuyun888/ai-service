# app/api/assistant.py
"""课次 11.01 · 业务助手 HTTP：POST /v1/assistant/chat（非流式先通）。

须带内部头（与 10.04 一致）：X-Internal-Token + X-Tenant-Id …
内部编排：retrieve → tool → generate（见 m11_01_assistant_integration）。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.lessons.m11_01_assistant_integration import run_assistant_turn
from app.security.internal_auth import InternalContext, require_internal_context

router = APIRouter(prefix="/v1", tags=["assistant"])
logger = logging.getLogger("ai-service.assistant")


class AssistantChatIn(BaseModel):
    """助手入参。"""

    message: str = Field(..., description="用户问题")
    session_id: str = Field(default="s1", description="会话 id")


class AssistantChatOut(BaseModel):
    """助手出参：回答 + 证据 + 轨迹。"""

    ok: bool
    reply: str
    session_id: str
    tenant_id: str
    evidence: dict[str, Any]
    trace: list[dict[str, Any]]
    decision_order: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0


@router.post("/assistant/chat", response_model=AssistantChatOut)
def assistant_chat(
    body: AssistantChatIn,
    ctx: InternalContext = Depends(require_internal_context),
) -> AssistantChatOut:
    """业务助手一轮：Harness + RAG + 只读 Tool。"""
    logger.info(
        "assistant_chat tenant=%s user=%s session=%s",
        ctx.tenant_id,
        ctx.user_id,
        body.session_id,
    )
    out = run_assistant_turn(
        body.message,
        tenant_id=ctx.tenant_id,
        session_id=body.session_id or "s1",
    )
    return AssistantChatOut(
        ok=bool(out.get("ok")),
        reply=str(out.get("reply") or ""),
        session_id=str(out.get("session_id") or body.session_id),
        tenant_id=str(out.get("tenant_id") or ctx.tenant_id),
        evidence=dict(out.get("evidence") or {}),
        trace=list(out.get("trace") or []),
        decision_order=list(out.get("decision_order") or []),
        elapsed_ms=int(out.get("elapsed_ms") or 0),
    )
