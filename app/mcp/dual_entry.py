# app/mcp/dual_entry.py
"""课次 09.04 · 同一业务实现的双入口：进程内 vs MCP Client。

推荐默认：
- 生产 Agent / Harness 热路径 → 进程内直接调 tools_*.py（低延迟）
- 开发 IDE（Cursor）→ MCP 暴露同一函数（好调、可发现）

禁止：复制粘贴两份业务逻辑。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]

EntryMode = Literal["inprocess", "mcp_stdio", "rest_style"]


def call_inventory_inprocess(sku: str) -> dict[str, Any]:
    """生产热路径：进程内直连纯函数。"""
    from app.mcp.tools_inventory import get_inventory

    text = get_inventory(sku)
    return {
        "mode": "inprocess",
        "tool": "get_inventory",
        "sku": sku,
        "result": text,
        "via": "app.mcp.tools_inventory.get_inventory",
    }


def call_inventory_rest_style(sku: str) -> dict[str, Any]:
    """REST 风格对照：同一实现，包成「HTTP 响应形状」（不强制起 uvicorn）。

    直觉：给人/网关的是 status+body；给模型 Client 的是 MCP tools/call。
    生产真 REST 可在 FastAPI 里一行转调 get_inventory。
    """
    from app.mcp.tools_inventory import get_inventory

    text = get_inventory(sku)
    ok = not text.startswith("error=")
    return {
        "mode": "rest_style",
        "tool": "get_inventory",
        "http": {
            "method": "GET",
            "path": f"/api/inventory/{sku}",
            "status": 200 if ok else 404,
            "body": text,
        },
        "via": "同一 get_inventory；外面包 HTTP 语义",
        "when": "多语言服务、公网/网关、非模型调用方",
    }


async def call_inventory_mcp_stdio(sku: str) -> dict[str, Any]:
    """开发期对齐 IDE：拉起 MCP Server，经 tools/call 取同一结果。"""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = [t.name for t in listed.tools]
            result = await session.call_tool(
                "get_inventory", arguments={"sku": sku}
            )
            texts: list[str] = []
            for block in result.content or []:
                t = getattr(block, "text", None)
                if t:
                    texts.append(t)
            body = "\n".join(texts)
            return {
                "mode": "mcp_stdio",
                "tool": "get_inventory",
                "sku": sku,
                "listed_tools": names,
                "result": body,
                "via": "MCP ClientSession.tools/call → server → tools_inventory",
            }


def dual_entry_same_sku(sku: str = "SHOE-RED-42") -> dict[str, Any]:
    """对照三入口：结果应来自同一实现（成功时文本一致）。"""
    plain = call_inventory_inprocess(sku)
    rest = call_inventory_rest_style(sku)
    mcp = asyncio.run(call_inventory_mcp_stdio(sku))
    same = (
        plain["result"] == mcp["result"]
        and rest["http"]["body"] == plain["result"]
    )
    return {
        "sku": sku,
        "inprocess": plain,
        "rest_style": rest,
        "mcp_stdio": mcp,
        "same_implementation_result": same,
        "lesson": "三入口共用 tools_inventory；生产优先进程内，IDE 用 MCP，网关用 REST",
    }
