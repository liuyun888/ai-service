# app/mcp/__init__.py
"""M09 MCP：工具发现与调用协议（概念 → Server → Schema → 客户端）。

09.01 先用进程内迷你协议讲清四要素；09.02 再换成官方 SDK + stdio。
"""

from app.mcp.concepts import (
    MiniMcpClient,
    MiniMcpServer,
    McpResource,
    McpTool,
    build_demo_server,
    contrast_plain_vs_mcp,
)

__all__ = [
    "MiniMcpClient",
    "MiniMcpServer",
    "McpResource",
    "McpTool",
    "build_demo_server",
    "contrast_plain_vs_mcp",
]
