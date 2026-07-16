# app/lessons/m09_02_mcp_server.py
"""课次 09.02 · 搭建 MCP Server：依赖、stdio 探针、Cursor 配置。"""

from __future__ import annotations

from typing import Any

from app.mcp.probe import cursor_config_snippet, demo_suite


def process_model_notes() -> list[dict[str, str]]:
    """进程模型小抄（口述用）。"""
    return [
        {
            "mode": "stdio",
            "how": "Client 拉起子进程，stdin/stdout 管道",
            "fit": "本地 IDE 调试（本课主路径）",
        },
        {
            "mode": "HTTP/SSE",
            "how": "独立常驻服务，网络访问",
            "fit": "团队共享 / 远程（进阶）",
        },
    ]


def lesson_suite() -> dict[str, Any]:
    """本课一键套件。"""
    suite = demo_suite()
    return {
        **suite,
        "process_models": process_model_notes(),
        "lifecycle": "启动 → 握手 initialize → tools/list →（09.03）tools/call 完善 Schema",
        "cursor_config": suite.get("cursor_config") or cursor_config_snippet(),
    }
