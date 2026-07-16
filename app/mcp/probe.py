# app/mcp/probe.py
"""课次 09.02 · 探针：不依赖 Cursor 也能验收 Server 活着。

两路验收：
1. 进程内：import FastMCP 实例并 list_tools（最快）
2. stdio：真拉起子进程，握手后 tools/list（对齐 IDE 拉起模型）
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]  # ai-service/


def check_import() -> dict[str, Any]:
    """依赖是否装好、server 模块是否可 import。"""
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401

        mcp_ok = True
        mcp_err = ""
    except ImportError as exc:
        mcp_ok = False
        mcp_err = str(exc)

    try:
        from app.mcp import server as srv

        server_ok = True
        server_name = getattr(srv.mcp, "name", "")
        server_err = ""
    except Exception as exc:  # noqa: BLE001
        server_ok = False
        server_name = ""
        server_err = f"{type(exc).__name__}: {exc}"

    return {
        "mcp_package_ok": mcp_ok,
        "mcp_error": mcp_err,
        "server_import_ok": server_ok,
        "server_name": server_name,
        "server_error": server_err,
        "ok": mcp_ok and server_ok,
    }


async def list_tools_inprocess() -> dict[str, Any]:
    """不启子进程：直接问 FastMCP 实例有哪些 Tool。"""
    from app.mcp.server import mcp

    tools = await mcp.list_tools()
    names = [t.name for t in tools]
    return {
        "mode": "inprocess",
        "tool_names": names,
        "has_search_docs": "search_docs" in names,
        "schemas": [
            {
                "name": t.name,
                "description": (t.description or "")[:120],
                "required": list((t.inputSchema or {}).get("required") or []),
            }
            for t in tools
        ],
    }


async def list_tools_via_stdio() -> dict[str, Any]:
    """真拉起 `python -m app.mcp.server`，走 stdio 握手 + tools/list。"""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    python = sys.executable
    params = StdioServerParameters(
        command=python,
        args=["-m", "app.mcp.server"],
        cwd=str(ROOT),
        # 继承环境，确保能找到已安装的 mcp
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            names = [t.name for t in result.tools]
            # 本课也可顺手 call 一下 mock，证明管道双向通
            call = await session.call_tool("search_docs", arguments={"query": "ping"})
            # call.content 多为 TextContent 列表
            texts: list[str] = []
            for block in call.content or []:
                text = getattr(block, "text", None)
                if text:
                    texts.append(text)
            return {
                "mode": "stdio",
                "command": python,
                "args": ["-m", "app.mcp.server"],
                "cwd": str(ROOT),
                "tool_names": names,
                "has_search_docs": "search_docs" in names,
                "call_texts": texts,
                "call_alive": any("server is alive" in t for t in texts),
            }


def assert_stderr_not_stdout_for_log() -> dict[str, Any]:
    """静态检查：server.py 的 log 不应写 stdout（抽样读源码）。"""
    src = (ROOT / "app" / "mcp" / "server.py").read_text(encoding="utf-8")
    uses_stderr = "file=sys.stderr" in src or "file=sys.stderr" in src.replace(" ", "")
    # 粗查：log 函数里若 print 到 stdout 会翻车
    bad_print = 'print(f"[mcp]' in src and "stderr" not in src[src.find("def log") : src.find("def log") + 200]
    return {
        "log_uses_stderr": "sys.stderr" in src and "def log" in src,
        "suspect_stdout_log": bad_print,
        "ok": "sys.stderr" in src and "def log" in src,
    }


def cursor_config_snippet() -> dict[str, Any]:
    """生成 Cursor MCP 配置片段（路径用本机绝对路径）。"""
    python = str(ROOT / ".venv" / "bin" / "python")
    return {
        "mcpServers": {
            "ai-service-tools": {
                "command": python,
                "args": ["-m", "app.mcp.server"],
                "cwd": str(ROOT),
            }
        }
    }


def demo_suite() -> dict[str, Any]:
    """同步入口：跑完 import / inprocess / stdio / stderr 检查。"""
    imp = check_import()
    if not imp["ok"]:
        return {
            "import": imp,
            "inprocess": None,
            "stdio": None,
            "stderr_check": assert_stderr_not_stdout_for_log(),
            "cursor_config": cursor_config_snippet(),
            "ok": False,
        }

    inproc = asyncio.run(list_tools_inprocess())
    stdio = asyncio.run(list_tools_via_stdio())
    stderr_check = assert_stderr_not_stdout_for_log()
    return {
        "import": imp,
        "inprocess": inproc,
        "stdio": stdio,
        "stderr_check": stderr_check,
        "cursor_config": cursor_config_snippet(),
        "ok": (
            imp["ok"]
            and inproc.get("has_search_docs")
            and stdio.get("has_search_docs")
            and stdio.get("call_alive")
            and stderr_check.get("ok")
        ),
    }
