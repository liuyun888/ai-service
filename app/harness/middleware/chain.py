# app/harness/middleware/chain.py
"""课次 08.06 · 中间件链：统一挂 before_tool / after_model / before_final 等钩子。

顺序有意义：鉴权在执行前；脱敏在落盘前；承诺护栏在最终出口。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from app.harness.middleware.guards import commitment_guard_event
from app.harness.middleware.redact import redact_event, redact_pii
from app.harness.middleware.safety import check_tool_allowed
from app.harness.middleware.token_log import log_usage_from_texts


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class MiddlewareContext:
    """一次请求在钩子间传递的上下文。"""

    user_text: str
    draft_reply: str = ""
    final_reply: str = ""
    tool_name: str = ""
    tool_observation: str = ""
    prompt_for_log: str = ""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    events: list[dict[str, Any]] = field(default_factory=list)
    blocked: bool = False


HookFn = Callable[[MiddlewareContext], None]


def _emit(ctx: MiddlewareContext, event: dict[str, Any]) -> None:
    row = {"at": _now(), **event}
    ctx.events.append(row)


def hook_before_tool(ctx: MiddlewareContext) -> None:
    """调用前：白名单鉴权。"""
    ok, msg = check_tool_allowed(ctx.tool_name) if ctx.tool_name else (True, "skip")
    _emit(
        ctx,
        {
            "hook": "before_tool",
            "middleware": "Authz",
            "tool": ctx.tool_name,
            "allowed": ok,
            "detail": msg,
        },
    )
    if not ok:
        ctx.blocked = True
        ctx.tool_observation = msg


def hook_after_tool(ctx: MiddlewareContext) -> None:
    """工具后：脱敏 Observation（再进 Trace）。"""
    ev = redact_event(ctx.tool_observation)
    ctx.tool_observation = str(ev["text"])
    _emit(ctx, ev)


def hook_after_model(ctx: MiddlewareContext) -> None:
    """模型后：Token 粗估日志。"""
    ev = log_usage_from_texts(
        ctx.trace_id,
        prompt=ctx.prompt_for_log or ctx.user_text,
        completion=ctx.draft_reply,
    )
    _emit(ctx, ev)


def hook_before_final(ctx: MiddlewareContext) -> None:
    """最终出口：绝对承诺护栏。"""
    ev = commitment_guard_event(ctx.draft_reply)
    ctx.final_reply = str(ev["output"])
    if ev.get("triggered"):
        ctx.blocked = True
    _emit(ctx, ev)


DEFAULT_HOOKS: list[tuple[str, HookFn]] = [
    ("before_tool", hook_before_tool),
    ("after_tool", hook_after_tool),
    ("after_model", hook_after_model),
    ("before_final", hook_before_final),
]


def run_middleware_pipeline(
    user_text: str,
    *,
    draft_reply: str,
    tool_name: str = "search_knowledge",
    tool_observation: str = "",
    prompt_for_log: str = "",
    skip_tool_hooks: bool = False,
) -> MiddlewareContext:
    """按约定顺序跑一遍横切钩子（主示例：承诺拦截 + Trace）。

    参数:
        user_text: 用户原话
        draft_reply: 模型「差点发出去」的风险草稿
        tool_name: 拟调用工具（演示 Authz）
        tool_observation: 工具原始输出（可含 PII）
        skip_tool_hooks: True 时跳过 before/after_tool（纯出口护栏场景）
    """
    ctx = MiddlewareContext(
        user_text=user_text,
        draft_reply=draft_reply,
        tool_name=tool_name,
        tool_observation=tool_observation or "",
        prompt_for_log=prompt_for_log or user_text,
    )

    if not skip_tool_hooks:
        hook_before_tool(ctx)
        if not ctx.blocked:
            # 模拟工具已执行：若 observation 空则用占位
            if not ctx.tool_observation:
                ctx.tool_observation = "ok"
            hook_after_tool(ctx)
        else:
            # 工具被拒也要记一条脱敏空跑可跳过
            pass

    # 即便工具被拒，仍可能有模型草稿（本课演示出口护栏）
    hook_after_model(ctx)
    hook_before_final(ctx)

    # Trace 落盘前再对 events 里敏感文本兜底（演示）
    for ev in ctx.events:
        if "output" in ev and isinstance(ev["output"], str):
            ev["output"] = redact_pii(ev["output"])
        if "text" in ev and isinstance(ev["text"], str):
            ev["text"] = redact_pii(ev["text"])

    return ctx
