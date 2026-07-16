# app/api/chat_stream.py
"""课次 10.03～10.04 · ai-service SSE 聊天流。

事件约定（JSON）：
  {"type":"token","text":"..."}
  {"type":"done","tenant_id":"...","user_id":"...","model_id":"...","request_id":"..."}
  {"type":"error","message":"..."}

10.04：必须带 X-Internal-Token + X-Tenant-Id；done 事件回显可信上下文，方便验收。
客户端断开后停止生成，避免模型空跑烧钱（本课用 mock sleep 模拟生成）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.security.internal_auth import InternalContext, require_internal_context

router = APIRouter(prefix="/v1", tags=["chat-stream"])
logger = logging.getLogger("ai-service.chat_stream")

# 可调：每个 token 间隔（秒）；改小打字更快，改大更容易观察流式
TOKEN_INTERVAL_SEC = 0.04


class ChatStreamBody(BaseModel):
    """流式聊天请求体。"""

    message: str = Field(default="", description="用户输入")


def _sse_data(payload: dict[str, Any]) -> str:
    """编码一行 SSE data 事件。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def iter_chat_tokens(
    message: str,
    *,
    ctx: InternalContext | None = None,
    request: Request | None = None,
    interval: float = TOKEN_INTERVAL_SEC,
) -> AsyncIterator[str]:
    """产出 token/done；若 request 已断开则提前结束。

    参数:
        message: 用户话术
        ctx: 10.04 可信上下文；有则写入 done，并打日志
        request: FastAPI Request；用于 is_disconnected
        interval: 每字间隔，模拟生成耗时
    """
    text = f"收到：{(message or '').strip() or '（空）'}（mock 流）"
    cancelled = False
    try:
        for ch in text:
            if request is not None and await request.is_disconnected():
                cancelled = True
                break
            yield _sse_data({"type": "token", "text": ch})
            if interval > 0:
                await asyncio.sleep(interval)
        if not cancelled:
            done: dict[str, Any] = {"type": "done"}
            if ctx is not None:
                done.update(
                    {
                        "tenant_id": ctx.tenant_id,
                        "user_id": ctx.user_id,
                        "model_id": ctx.model_id,
                        "request_id": ctx.request_id,
                    }
                )
            yield _sse_data(done)
    except asyncio.CancelledError:
        # 上游取消：不再继续 yield
        raise
    finally:
        # 这里可挂「取消下游模型请求」的钩子；mock 阶段只打标
        if cancelled and request is not None:
            # 供演示脚本通过自定义状态观察；生产写日志即可
            setattr(request.state, "sse_cancelled", True)


@router.get("/context/echo")
def context_echo(ctx: InternalContext = Depends(require_internal_context)) -> dict[str, str]:
    """非流式回显：验收「头是否到达」时不必拉整段 SSE。"""
    logger.info(
        "context_echo tenant=%s user=%s model=%s request_id=%s",
        ctx.tenant_id,
        ctx.user_id,
        ctx.model_id,
        ctx.request_id,
    )
    return {
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "model_id": ctx.model_id,
        "request_id": ctx.request_id,
    }


@router.post("/chat/stream")
async def chat_stream(
    body: ChatStreamBody,
    request: Request,
    ctx: InternalContext = Depends(require_internal_context),
) -> StreamingResponse:
    """SSE：边生成边推；须通过内部鉴权。"""

    logger.info(
        "chat_stream tenant=%s user=%s model=%s request_id=%s",
        ctx.tenant_id,
        ctx.user_id,
        ctx.model_id,
        ctx.request_id,
    )

    async def gen() -> AsyncIterator[str]:
        try:
            async for line in iter_chat_tokens(body.message, ctx=ctx, request=request):
                yield line
        except Exception as exc:  # noqa: BLE001
            yield _sse_data({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            # 提示中间层少缓冲（Nginx 等仍可能要单独关 proxy_buffering）
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
