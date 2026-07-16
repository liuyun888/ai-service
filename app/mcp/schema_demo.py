# app/mcp/schema_demo.py
"""课次 09.03 · Schema 对照 + list/call 验收（进程内 + stdio）。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def bad_vs_good_schema() -> dict[str, Any]:
    """坏例子 vs 好例子（口述/笔记用）。"""
    return {
        "bad": {
            "name": "do",
            "description": "做事",
            "params": "data: any",
            "why_bad": "模型不知道何时调、怎么传、错了怎么办",
        },
        "good": {
            "name": "get_inventory",
            "description": "按 SKU 查询可用库存；不要用于下单。SKU 需含颜色后缀。",
            "params": "sku: string (required)",
            "returns": 'JSON {sku, qty, warehouse} 或 error=...',
            "why_good": "何时用/不用、类型、例子、错误可回灌都写清",
        },
    }


def plain_vs_mcp_wiring() -> dict[str, Any]:
    """普通函数 vs MCP：同一业务，接线不同。"""
    from app.mcp.tools_inventory import get_inventory as plain_fn

    plain = plain_fn("SHOE-RED-42")
    return {
        "plain": {
            "how": "from app.mcp.tools_inventory import get_inventory; get_inventory(sku)",
            "must_import": True,
            "result": plain,
        },
        "mcp": {
            "how": "Client tools/list → tools/call name=get_inventory",
            "must_import": False,
            "shell": "业务仍是 tools_inventory.get_inventory；MCP 只是壳",
        },
    }


async def inspect_schemas() -> dict[str, Any]:
    """进程内 list：检查 description 含「不要」+ 参数有 description。"""
    from app.mcp.server import mcp

    tools = await mcp.list_tools()
    rows = []
    for t in tools:
        schema = t.inputSchema or {}
        props = schema.get("properties") or {}
        param_descs = {
            k: (v.get("description") or "") for k, v in props.items() if isinstance(v, dict)
        }
        desc = t.description or ""
        rows.append(
            {
                "name": t.name,
                "description": desc,
                "required": list(schema.get("required") or []),
                "param_descs": param_descs,
                "has_when_not": "不要" in desc,
                "params_documented": all(bool(d) for d in param_descs.values())
                if param_descs
                else False,
            }
        )
    names = [r["name"] for r in rows]
    return {
        "tool_names": names,
        "rows": rows,
        "has_get_inventory": "get_inventory" in names,
        "all_have_when_not": all(r["has_when_not"] for r in rows),
        "all_params_documented": all(r["params_documented"] for r in rows),
    }


async def call_via_stdio() -> dict[str, Any]:
    """stdio：成功 call + 错误可回灌 call。"""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )

    def _text(result: Any) -> str:
        parts: list[str] = []
        for block in result.content or []:
            t = getattr(block, "text", None)
            if t:
                parts.append(t)
        return "\n".join(parts)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = [t.name for t in listed.tools]

            ok = await session.call_tool(
                "get_inventory", arguments={"sku": "SHOE-RED-42"}
            )
            bad = await session.call_tool(
                "get_inventory", arguments={"sku": "NO-SUCH-SKU"}
            )
            ship = await session.call_tool(
                "get_shipment", arguments={"tracking_no": "SF1234567890"}
            )
            search = await session.call_tool(
                "search_docs", arguments={"query": "已拆封"}
            )

            ok_text = _text(ok)
            bad_text = _text(bad)
            return {
                "tool_names": names,
                "success_text": ok_text,
                "error_text": bad_text,
                "shipment_text": _text(ship),
                "search_preview": _text(search)[:200],
                "success_has_qty": '"qty"' in ok_text or "qty" in ok_text,
                "error_is_soft": bad_text.startswith("error=") or "error=not_found" in bad_text,
                "no_traceback": "Traceback" not in bad_text,
            }


def unit_plain_functions() -> dict[str, Any]:
    """不经 MCP：纯函数单测风格断言。"""
    from app.mcp.tools_inventory import get_inventory, get_shipment

    ok = get_inventory("SHOE-RED-42")
    bad = get_inventory("ZZZ")
    empty = get_inventory("")
    ship = get_shipment("SF1234567890")
    data = json.loads(ok)
    return {
        "ok_qty": data.get("qty"),
        "bad_soft": bad.startswith("error="),
        "empty_soft": empty.startswith("error="),
        "ship_ok": "in_transit" in ship,
        "layered": True,
    }


def demo_suite() -> dict[str, Any]:
    """本课一键套件。"""
    schemas = asyncio.run(inspect_schemas())
    calls = asyncio.run(call_via_stdio())
    return {
        "bad_vs_good": bad_vs_good_schema(),
        "wiring": plain_vs_mcp_wiring(),
        "schemas": schemas,
        "calls": calls,
        "unit": unit_plain_functions(),
        "ok": (
            schemas.get("has_get_inventory")
            and schemas.get("all_have_when_not")
            and schemas.get("all_params_documented")
            and calls.get("success_has_qty")
            and calls.get("error_is_soft")
            and calls.get("no_traceback")
        ),
    }
