# app/mcp/selection.py
"""课次 09.04 · MCP / REST / 进程内 选型矩阵（可跑、可写入笔记）。"""

from __future__ import annotations

from typing import Any


def selection_matrix() -> list[dict[str, str]]:
    """三扇门：按场景选拓扑。"""
    return [
        {
            "way": "进程内函数",
            "best_for": "生产热路径、低延迟 Agent/Harness",
            "watch": "与 app 同发版；改 Tool 要发应用",
            "example": "from app.mcp.tools_inventory import get_inventory",
        },
        {
            "way": "MCP",
            "best_for": "IDE 调试、多 Client 复用同一工具箱、本地资源",
            "watch": "stdio 生命周期、版本与 Client 协同；勿为统一强行上生产热路径",
            "example": "Cursor → -m app.mcp.server → get_inventory",
        },
        {
            "way": "REST",
            "best_for": "多语言服务、公网/网关、非模型调用方",
            "watch": "自建鉴权与 OpenAPI 文档；粒度按 HTTP 资源设计",
            "example": "GET /api/inventory/{sku} → 转调同一纯函数",
        },
    ]


def choose(scenario: str) -> dict[str, Any]:
    """根据场景关键词给出建议（演示用规则，非万能决策树）。"""
    s = scenario or ""
    if any(k in s for k in ("IDE", "Cursor", "调试", "本地试")):
        return {
            "scenario": s,
            "pick": "MCP",
            "reason": "开发期发现+试调最快；与生产函数同源",
        }
    if any(k in s for k in ("网关", "公网", "多语言", "前端直调", "OpenAPI")):
        return {
            "scenario": s,
            "pick": "REST",
            "reason": "非模型调用方 / 跨语言，走 HTTP 更合适",
        }
    if any(k in s for k in ("生产", "热路径", "低延迟", "Agent 运行时", "Harness")):
        return {
            "scenario": s,
            "pick": "进程内函数",
            "reason": "少一次进程跳；Harness 直接 import 纯函数",
        }
    return {
        "scenario": s,
        "pick": "进程内函数",
        "reason": "默认保守：先进程内；需要 IDE 调试再暴露 MCP",
    }


def harness_integration_policy() -> dict[str, Any]:
    """接入 Harness 的两档深度（大多数产品先走仅开发）。"""
    return {
        "level_1_dev_only": {
            "title": "仅开发",
            "desc": "Harness/Agent 不依赖 MCP；Cursor 单独连 Server 调 Tool",
            "recommend": True,
        },
        "level_2_runtime_client": {
            "title": "运行时内嵌 MCP Client",
            "desc": "Harness 启动时连 Server；适合工具要给多个运行时共用",
            "recommend": False,
            "when": "多宿主复用且不愿每宿主复制绑定代码时再上",
        },
        "one_liner": "开发调试走 MCP，生产热路径进程内直连同一 tools_*.py",
    }


def security_checklist() -> list[dict[str, str]]:
    """安全提醒（验收要能勾）。"""
    return [
        {
            "item": "MCP Server ≈ 高权限插件",
            "do": "能读本地/内网的 Tool 默认只读；敏感目录拒绝",
        },
        {
            "item": "密钥",
            "do": "不要把生产密钥塞进 MCP 配置「反正本机」；Tool 内做租户校验",
        },
        {
            "item": "写入类 Tool",
            "do": "默认不进 MCP；若暴露必须 HITL / 鉴权（见 M07）",
        },
        {
            "item": "本课工具箱",
            "do": "search_docs / get_inventory / get_shipment 均为只读",
        },
    ]
