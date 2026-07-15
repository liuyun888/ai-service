# app/harness/middleware/trace.py
"""课次 08.06 · 自建 JSON Trace：可回放、可离线抽检。

生产可对接 LangSmith；没有平台时，先落到 notes/traces/ 也能迭代中间件。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.harness.middleware.chain import MiddlewareContext
from app.harness.middleware.redact import redact_pii


def build_trace_document(
    ctx: MiddlewareContext,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把中间件上下文打成可回放文档（已脱敏）。"""
    doc: dict[str, Any] = {
        "trace_id": ctx.trace_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input": {"user_text": redact_pii(ctx.user_text)},
        "draft_reply": redact_pii(ctx.draft_reply),
        "final_reply": redact_pii(ctx.final_reply),
        "tool": {
            "name": ctx.tool_name,
            "observation": redact_pii(ctx.tool_observation),
        },
        "blocked": ctx.blocked,
        "events": ctx.events,
        "platform_note": "可导出到 LangSmith；本课先用自建 JSON",
    }
    if extra:
        doc["extra"] = extra
    return doc


def export_trace(
    ctx: MiddlewareContext,
    path: Path | str,
    *,
    extra: dict[str, Any] | None = None,
) -> Path:
    """写入 JSON 文件，返回绝对路径。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = build_trace_document(ctx, extra=extra)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return p.resolve()
