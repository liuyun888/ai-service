# app/lifecycle.py
"""课次 13.01 · 进程生命周期钩子（配合容器 SIGTERM / 优雅停机）。

直觉：Docker stop 会发 SIGTERM → uvicorn 停止接新连接 →
本模块在 shutdown 时打日志，提醒「进行中的 SSE/长请求应尽快结束」。
真正断流逻辑仍由各路由的 is_disconnected / Abort 处理（见 10.03）。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger("ai-service.lifecycle")


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    """FastAPI lifespan：启动 / 关闭各执行一次。"""
    logger.info("ai-service 启动完成（ready）；健康检查走 GET /health")
    try:
        yield
    finally:
        # 容器收到 SIGTERM 进入此处：不要在这里 sleep 很久
        logger.info(
            "ai-service 正在优雅停机：停止接新请求；"
            "进行中的流式/长请求应自行感知断开并退出"
        )
