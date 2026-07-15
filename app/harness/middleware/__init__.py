# app/harness/middleware/__init__.py
"""中间件：安全边界（06.06）+ 钩子链 / 压缩 / Trace（08.06）。"""

from app.harness.middleware.chain import run_middleware_pipeline
from app.harness.middleware.compaction import compact_messages
from app.harness.middleware.guards import commitment_guard
from app.harness.middleware.safety import (
    TOOL_WHITELIST,
    check_tool_allowed,
    guard_output,
    should_escalate,
)
from app.harness.middleware.trace import export_trace

__all__ = [
    "TOOL_WHITELIST",
    "check_tool_allowed",
    "commitment_guard",
    "compact_messages",
    "export_trace",
    "guard_output",
    "run_middleware_pipeline",
    "should_escalate",
]
