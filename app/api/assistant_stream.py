# app/api/assistant_stream.py
"""课次 11.05 · 统一助手 SSE：POST /v1/assistant/stream。

浏览器经 BFF 打到这里；先编排出完整回复，再按字推 token（打字机），
done 事件带回 mode/action/护栏等元数据，方便前端验收「真助手」而非 mock。

与 /v1/chat/stream（10.03 mock）并存：教学 mock 不删，正式聊天走本路由。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.lessons.m11_05_unified_assistant import run_unified_turn
from app.security.internal_auth import InternalContext, require_internal_context

router = APIRouter(prefix="/v1", tags=["assistant-stream"])
logger = logging.getLogger("ai-service.assistant_stream")

# 可调：每个字间隔（秒）；改小更快，改大更易观察流式
TOKEN_INTERVAL_SEC = 0.02


class AssistantStreamBody(BaseModel):
    """流式助手请求体。"""

    message: str = Field(default="", description="用户输入")
    session_id: str = Field(default="", description="会话 id；空则用 user_id 兜底")


def _sse_data(payload: dict[str, Any]) -> str:
    """编码一行 SSE data 事件。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def iter_assistant_tokens(
    message: str,
    *,
    ctx: InternalContext,
    request: Request | None = None,
    session_id: str = "",
    interval: float = TOKEN_INTERVAL_SEC,
) -> AsyncIterator[str]:
    """先同步编排，再异步推字；断开则停。"""
    sid = (session_id or "").strip() or f"u-{ctx.user_id or 'anon'}"
    # 编排是 CPU/IO 同步；放进线程池避免堵住事件循环太久（库存/检索可能稍慢）
    result = await asyncio.to_thread(
        run_unified_turn,
        message,
        tenant_id=ctx.tenant_id,
        session_id=sid,
        request_id=ctx.request_id,
        user_id=ctx.user_id,
    )
    reply = str(result.get("reply") or "") or "（空回复）"
    cancelled = False
    try:
        for ch in reply:
            if request is not None and await request.is_disconnected():
                cancelled = True
                break
            yield _sse_data({"type": "token", "text": ch})
            if interval > 0:
                await asyncio.sleep(interval)
        if not cancelled:
            done: dict[str, Any] = {
                "type": "done",
                "tenant_id": ctx.tenant_id,
                "user_id": ctx.user_id,
                "model_id": ctx.model_id,
                "request_id": ctx.request_id,
                "session_id": result.get("session_id") or sid,
                "mode": result.get("mode"),
                "action": result.get("action"),
                "guard_triggered": bool(result.get("guard_triggered")),
                "case_id": result.get("case_id") or "",
                "ok": bool(result.get("ok")),
                "elapsed_ms": int(result.get("elapsed_ms") or 0),
            }
            if result.get("summary"):
                done["summary"] = result["summary"]
            yield _sse_data(done)
    except asyncio.CancelledError:
        raise
    finally:
        if cancelled and request is not None:
            setattr(request.state, "sse_cancelled", True)


@router.post("/assistant/stream")
async def assistant_stream(
    body: AssistantStreamBody,
    request: Request,
    ctx: InternalContext = Depends(require_internal_context),
) -> StreamingResponse:
    """统一助手 SSE：须带内部头。"""
    logger.info(
        "assistant_stream tenant=%s user=%s request_id=%s msg_len=%s",
        ctx.tenant_id,
        ctx.user_id,
        ctx.request_id,
        len(body.message or ""),
    )

    async def gen() -> AsyncIterator[str]:
        try:
            async for line in iter_assistant_tokens(
                body.message,
                ctx=ctx,
                request=request,
                session_id=body.session_id,
            ):
                yield line
        except Exception as exc:  # noqa: BLE001
            yield _sse_data({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
