# app/mcp/server.py
"""课次 09.02 · 最小可启动 MCP Server（stdio）。

进程模型：Cursor / 探针 Client 拉起本进程，经 stdin/stdout 走 MCP 协议。
大忌：不要往 stdout print 调试信息——会弄脏协议帧；日志一律 stderr。

本课 Tool 先 mock，证明「能启动 + 能 list」；真业务 Schema 见 09.03。
"""

from __future__ import annotations

import sys


def log(msg: str) -> None:
    """只写 stderr，绝不碰 stdout。"""
    print(f"[mcp] {msg}", file=sys.stderr, flush=True)


try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    log(f"ImportError: 请先 pip install mcp  ({exc})")
    raise

# Server 名：Client 配置里常对应 mcpServers 的 key 旁白
mcp = FastMCP("ai-service-tools")


@mcp.tool()
def search_docs(query: str) -> str:
    """按关键词搜索知识库（本课为 mock，证明管道通）。

    参数:
        query: 搜索关键词
    """
    log(f"search_docs query={query!r}")
    return f"mock: no hits for {query!r}; server is alive"


def main() -> None:
    """入口：默认 stdio transport，前台会「卡住」等 Client——属正常。"""
    log("starting MCP server (stdio); logs go to stderr only")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
