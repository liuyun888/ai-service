# app/lessons/m09_04_client_integration.py
"""课次 09.04 · Client 接入、选型、双入口对照（收束 M09）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.mcp.dual_entry import dual_entry_same_sku
from app.mcp.probe import cursor_config_snippet
from app.mcp.selection import (
    choose,
    harness_integration_policy,
    security_checklist,
    selection_matrix,
)

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "app" / "mcp" / "README.md"


def ensure_cursor_config(notes_dir: Path | None = None) -> dict[str, Any]:
    """写出/刷新 Cursor MCP 配置 JSON。"""
    notes = notes_dir or (ROOT / "notes")
    notes.mkdir(parents=True, exist_ok=True)
    path = notes / "cursor_mcp_ai_service_tools.json"
    cfg = cursor_config_snippet()
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(path), "config": cfg}


def readme_checklist() -> dict[str, Any]:
    """验收 README 是否写清选型关键词。"""
    text = README.read_text(encoding="utf-8") if README.exists() else ""
    keys = ["何时用 MCP", "何时不用", "进程内", "REST", "双入口", "只读"]
    missing = [k for k in keys if k not in text]
    return {
        "path": str(README),
        "exists": README.exists(),
        "missing": missing,
        "ok": README.exists() and not missing,
    }


def no_duplicated_business_logic() -> dict[str, Any]:
    """粗检：server 薄壳应 import tools_，而不是内嵌第二份 MOCK_DB。"""
    server_src = (ROOT / "app" / "mcp" / "server.py").read_text(encoding="utf-8")
    inv_src = (ROOT / "app" / "mcp" / "tools_inventory.py").read_text(encoding="utf-8")
    return {
        "server_imports_tools": "from app.mcp.tools_inventory import" in server_src
        or "from app.mcp.tools_search import" in server_src,
        "mock_db_only_in_tools": "MOCK_DB" in inv_src and "MOCK_DB" not in server_src,
        "ok": ("tools_inventory" in server_src or "tools_search" in server_src)
        and "MOCK_DB" not in server_src,
    }


def demo_suite(*, notes_dir: Path | None = None) -> dict[str, Any]:
    """本课一键套件。"""
    cfg = ensure_cursor_config(notes_dir)
    dual = dual_entry_same_sku("SHOE-RED-42")
    scenarios = [
        choose("Cursor 里调试 get_inventory"),
        choose("生产 Harness 热路径查库存"),
        choose("给外部网关 OpenAPI 暴露库存"),
    ]
    return {
        "cursor": cfg,
        "matrix": selection_matrix(),
        "scenarios": scenarios,
        "harness": harness_integration_policy(),
        "security": security_checklist(),
        "dual": dual,
        "readme": readme_checklist(),
        "no_dup": no_duplicated_business_logic(),
        "ok": (
            dual.get("same_implementation_result")
            and readme_checklist()["ok"]
            and no_duplicated_business_logic()["ok"]
            and "get_inventory" in (dual.get("mcp_stdio") or {}).get("listed_tools", [])
        ),
    }
