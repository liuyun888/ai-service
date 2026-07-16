# app/ops/column_checklist.py
"""课次 13.02 · 专栏里程碑自检：环境里「已具备 / 待补」对照表。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 路径相对 ai-service 根；存在即算「本仓库侧已具备」
MILESTONE_FILES: list[dict[str, str]] = [
    {"id": "M00", "item": "health 可访问", "path": "app/main.py"},
    {"id": "M03", "item": "RAG 问答链", "path": "app/lessons/m03_02_qa_chain.py"},
    {"id": "M08", "item": "Harness 中间件/Trace", "path": "app/harness/middleware/trace.py"},
    {"id": "M10", "item": "SSE 流式", "path": "app/api/chat_stream.py"},
    {"id": "M11", "item": "统一助手流", "path": "app/api/assistant_stream.py"},
    {"id": "M12", "item": "抽取 API", "path": "app/api/extract.py"},
    {"id": "M13.01", "item": "Compose/Dockerfile", "path": "docker-compose.yml"},
    {"id": "M13.02", "item": "成本/金标模块", "path": "app/ops/cost.py"},
    {"id": "test", "item": "Harness 单测", "path": "tests/test_harness.py"},
]


def column_self_check(project_root: Path | None = None) -> dict[str, Any]:
    """扫描关键文件，输出具备/待补。"""
    root = project_root or Path(__file__).resolve().parents[2]
    rows = []
    for item in MILESTONE_FILES:
        p = root / item["path"]
        rows.append(
            {
                "id": item["id"],
                "item": item["item"],
                "path": item["path"],
                "ready": p.is_file(),
            }
        )
    ready = [r for r in rows if r["ready"]]
    pending = [r for r in rows if not r["ready"]]
    return {
        "ready": ready,
        "pending": pending,
        "ready_count": len(ready),
        "total": len(rows),
        "ok": len(pending) == 0,
    }
