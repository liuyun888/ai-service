# app/mcp/server.py
"""课次 09.02～09.03 · MCP Server（stdio）+ 带 Schema 的可发现 Tool。

09.02：进程可启动、日志走 stderr。
09.03：业务进 tools_*.py；此处只做薄注册 + 清晰 docstring/Field。
"""

from __future__ import annotations

import sys
from typing import Annotated

from pydantic import Field


def log(msg: str) -> None:
    """只写 stderr，绝不碰 stdout。"""
    print(f"[mcp] {msg}", file=sys.stderr, flush=True)


try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    log(f"ImportError: 请先 pip install mcp  ({exc})")
    raise

mcp = FastMCP("ai-service-tools")


@mcp.tool()
def search_docs(
    query: Annotated[str, Field(description="搜索关键词，如「已拆封」；不要传整段文章")],
) -> str:
    """按关键词搜索知识库；不要用于写入或删改文件。适合找政策/投诉摘要片段。"""
    from app.mcp.tools_search import search_docs as _impl

    log(f"search_docs query={query!r}")
    return _impl(query)


@mcp.tool()
def get_inventory(
    sku: Annotated[
        str,
        Field(description="SKU，须含颜色尺码后缀，示例 SHOE-RED-42"),
    ],
) -> str:
    """按 SKU 查询可用库存；不要用于下单或改库存。返回短 JSON {sku,qty,warehouse}。"""
    from app.mcp.tools_inventory import get_inventory as _impl

    log(f"get_inventory sku={sku!r}")
    return _impl(sku)


@mcp.tool()
def get_shipment(
    tracking_no: Annotated[
        str,
        Field(description="运单号，示例 SF1234567890"),
    ],
) -> str:
    """按运单号查询物流状态；不要用于改地址或拦截件。返回短 JSON 或 error=。"""
    from app.mcp.tools_inventory import get_shipment as _impl

    log(f"get_shipment tracking_no={tracking_no!r}")
    return _impl(tracking_no)


def main() -> None:
    """入口：默认 stdio；前台卡住等 Client 属正常。"""
    log("starting MCP server (stdio); tools=search_docs,get_inventory,get_shipment")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
