# app/api/chat_stream.py
"""课次 10.03 · ai-service SSE 聊天流。

事件约定（JSON）：
  {"type":"token","text":"..."}
  {"type":"done"}
  {"type":"error","message":"..."}

客户端断开后停止生成，避免模型空跑烧钱（本课用 mock sleep 模拟生成）。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1", tags=["chat-stream"])

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
    request: Request | None = None,
    interval: float = TOKEN_INTERVAL_SEC,
) -> AsyncIterator[str]:
    """产出 token/done；若 request 已断开则提前结束。

    参数:
        message: 用户话术
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
            yield _sse_data({"type": "done"})
    except asyncio.CancelledError:
        # 上游取消：不再继续 yield
        raise
    finally:
        # 这里可挂「取消下游模型请求」的钩子；mock 阶段只打标
        if cancelled and request is not None:
            # 供演示脚本通过自定义状态观察；生产写日志即可
            setattr(request.state, "sse_cancelled", True)


@router.post("/chat/stream")
async def chat_stream(body: ChatStreamBody, request: Request) -> StreamingResponse:
    """SSE：边生成边推；Content-Type=text/event-stream。"""

    async def gen() -> AsyncIterator[str]:
        try:
            async for line in iter_chat_tokens(body.message, request=request):
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
