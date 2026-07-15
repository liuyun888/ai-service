# app/lessons/m08_06_middleware_eval.py
"""课次 08.06 · Middleware + Compaction + Trace；收束 M08 里程碑。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.harness.middleware.chain import run_middleware_pipeline
from app.harness.middleware.compaction import build_long_fake_dialog, compact_messages
from app.harness.middleware.guards import commitment_guard
from app.harness.middleware.trace import export_trace

# 主示例用户话术（与正文一致）
DEMO_USER = "保证明天一定到货。"
# 模型差点发出去的风险草稿
DEMO_DRAFT = "好的，保证明天一定到货，请放心。"
# 工具 Observation 含 PII，用于脱敏演示
DEMO_TOOL_OBS = (
    "物流查询：用户手机 13800138000，证件 110101199001011234，"
    "当前在途。原始报文很长……" + ("详情" * 40)
)

# M08 里程碑对照：课号 → 能力（口述自检用）
M08_MILESTONE: list[dict[str, str]] = [
    {"id": "08.01", "capability": "Harness 外壳（鉴权/护栏/Trace 对照）", "path": "app/harness/shell.py"},
    {"id": "08.02", "capability": "五维工程打分与缺口表", "path": "app/harness/five_dimensions.py"},
    {"id": "08.03", "capability": "Context Eng：VFS 按需 read", "path": "app/harness/context/vfs.py"},
    {"id": "08.04", "capability": "Deep：write_todos + max_steps", "path": "app/harness/deep_agent.py"},
    {"id": "08.05", "capability": "子 Agent 委派 + Memory Store", "path": "app/harness/subagent.py"},
    {"id": "08.06", "capability": "Middleware / Compaction / Trace", "path": "app/harness/middleware/chain.py"},
]


def run_commitment_demo() -> dict[str, Any]:
    """合规拦截 + TokenLog + 脱敏 主路径。"""
    ctx = run_middleware_pipeline(
        DEMO_USER,
        draft_reply=DEMO_DRAFT,
        tool_name="search_knowledge",
        tool_observation=DEMO_TOOL_OBS,
        prompt_for_log=f"system…\nuser:{DEMO_USER}",
    )
    guard_events = [e for e in ctx.events if e.get("middleware") == "CommitmentGuard"]
    token_events = [e for e in ctx.events if e.get("middleware") == "TokenLog"]
    redact_events = [e for e in ctx.events if e.get("middleware") == "PIIRedact"]
    return {
        "ctx": ctx,
        "user": DEMO_USER,
        "draft": DEMO_DRAFT,
        "final": ctx.final_reply,
        "guard_triggered": bool(guard_events and guard_events[0].get("triggered")),
        "token_logged": bool(token_events),
        "pii_redacted": bool(redact_events and redact_events[0].get("changed")),
        "hooks": [e.get("hook") for e in ctx.events],
    }


def run_authz_deny_demo() -> dict[str, Any]:
    """before_tool 拒绝高置信退款 Tool。"""
    ctx = run_middleware_pipeline(
        "给我直接退款",
        draft_reply="已为您退款完成",  # 仍会被 before_final 拦
        tool_name="refund",
        tool_observation="",
        skip_tool_hooks=False,
    )
    authz = next((e for e in ctx.events if e.get("middleware") == "Authz"), {})
    return {
        "allowed": authz.get("allowed"),
        "detail": authz.get("detail"),
        "final": ctx.final_reply,
        "events": ctx.events,
    }


def run_compaction_demo(*, turns: int = 20, keep_recent: int = 8) -> dict[str, Any]:
    """20 轮假对话压缩前后字符对比。"""
    msgs = build_long_fake_dialog(turns=turns)
    result = compact_messages(msgs, keep_recent=keep_recent)
    return {
        "turns": turns,
        "message_count_before": len(msgs),
        "message_count_after": len(result["messages"]),
        "before_chars": result["before_chars"],
        "after_chars": result["after_chars"],
        "saved_chars": result.get("saved_chars", 0),
        "compacted": result["compacted"],
        "pointers": result["pointers"],
        "summary": result["summary"],
        "kept_system": any(
            "硬约束" in (m.get("content") or "") for m in result["messages"] if m.get("role") == "system"
        ),
    }


def self_check_milestone(project_root: Path | None = None) -> dict[str, Any]:
    """对照里程碑：检查关键文件是否存在（具备多项能力）。"""
    root = project_root or Path(__file__).resolve().parents[2]
    rows = []
    for item in M08_MILESTONE:
        p = root / item["path"]
        rows.append(
            {
                "id": item["id"],
                "capability": item["capability"],
                "path": item["path"],
                "exists": p.is_file(),
            }
        )
    return {
        "rows": rows,
        "ready_count": sum(1 for r in rows if r["exists"]),
        "total": len(rows),
        "ok": all(r["exists"] for r in rows),
    }


def demo_suite(*, notes_dir: Path | None = None) -> dict[str, Any]:
    """本课一键套件：护栏链路 + 压缩 + Trace 导出 + 里程碑。"""
    root = notes_dir or Path(__file__).resolve().parents[2] / "notes"
    commit = run_commitment_demo()
    authz = run_authz_deny_demo()
    compact = run_compaction_demo()
    trace_path = export_trace(
        commit["ctx"],
        root / "traces" / "trace-demo.json",
        extra={
            "scenario": "commitment_guard",
            "compaction_preview": {
                "before": compact["before_chars"],
                "after": compact["after_chars"],
                "pointers": compact["pointers"],
            },
            "deep_todos_hint": "可把 08.04 trajectory 一并挂到 extra",
        },
    )
    milestone = self_check_milestone()
    ok_pass, _ = commitment_guard("当前物流显示已发货")
    ok_block, _ = commitment_guard("保证明天一定到货")
    return {
        "commitment": commit,
        "authz": authz,
        "compaction": compact,
        "trace_path": str(trace_path),
        "milestone": milestone,
        "unit_guard": {"pass_safe": ok_pass, "block_risk": not ok_block},
    }
