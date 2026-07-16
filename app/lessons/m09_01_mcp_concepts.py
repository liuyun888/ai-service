# app/lessons/m09_01_mcp_concepts.py
"""课次 09.01 · MCP 概念：四要素 + 普通 Tool 对照 + 三问笔记。"""

from __future__ import annotations

from typing import Any

from app.mcp.concepts import (
    MiniMcpClient,
    build_demo_server,
    contrast_plain_vs_mcp,
    four_elements_cheatsheet,
    topology_ascii,
)

# 本模块计划第一个业务 Tool（与正文/09.02 对齐）
FIRST_TOOL_NAME = "search_docs"
FIRST_TOOL_PARAMS = ["query: str  # 搜索关键词"]


def answer_three_questions() -> dict[str, Any]:
    """正文三问的标准答（笔记可对照改成你自己的）。"""
    return {
        "q1_client": "Cursor（或你的 Agent 运行时）——连接并调用的一方",
        "q1_server": "ai-service-tools（迷你/后续真 MCP Server）——暴露能力的进程",
        "q2_first_tool": FIRST_TOOL_NAME,
        "q3_params": FIRST_TOOL_PARAMS,
    }


def demo_tool_vs_resource() -> dict[str, Any]:
    """验收：不要把 Resource 和 Tool 混为一谈。"""
    server = build_demo_server()
    client = MiniMcpClient(server)
    tools = client.discover()["tools"]
    resources = client.discover()["resources"]
    call = client.call("search_docs", query="已拆封")
    read = client.read("policy://return")
    # 反例：把 Resource URI 当 Tool 名去 call
    wrong = client.call("policy://return", query="x")
    return {
        "tool_names": [t["name"] for t in tools],
        "resource_uris": [r["uri"] for r in resources],
        "call_ok": call.get("ok"),
        "read_ok": read.get("ok"),
        "call_resource_as_tool_fails": wrong.get("ok") is False,
        "rule": "Tool=动作(call)；Resource=可读数据(read)；URI 不是 Tool 名",
    }


def demo_suite() -> dict[str, Any]:
    """本课一键套件。"""
    return {
        "elements": four_elements_cheatsheet(),
        "topology": topology_ascii(),
        "contrast": contrast_plain_vs_mcp("已拆封"),
        "tool_vs_resource": demo_tool_vs_resource(),
        "three_questions": answer_three_questions(),
        "first_tool": FIRST_TOOL_NAME,
    }
