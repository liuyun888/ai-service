# app/lessons/m08_01_model_plus_harness.py
"""课次 08.01 · Agent = Model + Harness：目录骨架检查 + 对照包装。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.harness.shell import (
    contrast_return_policy,
    gap_audit_template,
    layer_map,
)

ROOT = Path(__file__).resolve().parents[2]  # ai-service/


def expected_harness_dirs() -> list[str]:
    """本课要求的目录骨架。"""
    return [
        "app/harness/middleware",
        "app/harness/context",
        "app/harness/memory",
        "app/harness/skills",
    ]


def check_harness_skeleton() -> dict[str, Any]:
    """检查骨架目录是否存在。"""
    rows = []
    for rel in expected_harness_dirs():
        p = ROOT / rel
        rows.append({"path": rel, "exists": p.is_dir()})
    return {
        "root": str(ROOT),
        "rows": rows,
        "ok": all(r["exists"] for r in rows),
    }


def demo_contrast() -> dict[str, Any]:
    return contrast_return_policy("退货要几天？")
