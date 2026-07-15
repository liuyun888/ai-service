# app/harness/middleware/safety.py
"""课次 06.06 · 人机协作与安全边界（最小可跑中间件）。

四层边界里，本文件先落三块（代码强制，不只写在 System）：
1. 工具白名单：不在名单的 Tool 直接拒绝调用
2. 输出护栏：拦截绝对承诺 / 诊断式话术
3. 转人工 / HITL：高风险诉求暂停，附带上下文摘要

调了这些旋钮会怎样：
- 放宽 BLOCK_PATTERNS → 更多风险句可能漏出去
- 收紧 TOOL_WHITELIST → 只读能力变少，但更安全
- TOOL_FAIL_THRESHOLD 调小 → 更容易转人工
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 可调开关（给小白：改数字/列表前先想清楚业务后果）
# ---------------------------------------------------------------------------

# 只读 Tool 白名单：模型即便 hallucinate 出「refund」也不让真调
TOOL_WHITELIST: frozenset[str] = frozenset(
    {
        "get_inventory",
        "get_shipment",
        "search_knowledge",
        "get_course",
    }
)

# 高风险动作名：出现在「准备调用的 Tool」或用户明确诉求时 → HITL，不自动执行
HIGH_RISK_ACTIONS: frozenset[str] = frozenset(
    {
        "refund",
        "create_refund",
        "change_address",
        "grant_permission",
        "prescribe",  # 开药类（本课只有名称层拦截示意）
    }
)

# 输出层：这些短语一旦出现在即将发出的回复里，整段换成安全模板
BLOCK_PATTERNS: tuple[str, ...] = (
    "保证明天",
    "一定治愈",
    "稳赚不赔",
    "100%有效",
    "绝对能到",
    "保证退款到账",
)

# 转人工：工具连续失败达到阈值
TOOL_FAIL_THRESHOLD = 2

# 用户话术触发转人工的关键词
ESCALATE_KEYWORDS: tuple[str, ...] = (
    "人工",
    "投诉",
    "找经理",
    "曝光",
    "律师",
)

SAFE_REFUSAL_TEMPLATE = (
    "我不能做出该类绝对承诺或诊断式结论。"
    "我可以说明通常规则，或帮你转人工确认。请补充订单号/诉求要点。"
)

HITL_REFUND_TEMPLATE = (
    "已生成退款申请草稿，**待人工确认后**才会执行，我不会直接调退款接口。"
    "请稍候客服接手；下面是给人工的摘要。"
)


@dataclass
class GuardResult:
    """输出护栏结果。"""

    ok: bool
    text: str
    hit_pattern: str = ""


@dataclass
class EscalateDecision:
    """是否转人工 / HITL。"""

    escalate: bool
    reason: str
    kind: str = ""  # human | hitl_refund | tool_fails | whitelist | ""


@dataclass
class SafetyContext:
    """一次请求可附带的上下文，用于转人工摘要。"""

    user_text: str = ""
    session_id: str = "default"
    tool_fails: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)
    pending_action: str = ""


def check_tool_allowed(tool_name: str) -> tuple[bool, str]:
    """调用前检查：不在白名单 → 拒绝（返回给模型/编排层的可读原因）。"""
    name = (tool_name or "").strip()
    if not name:
        return False, "error=empty_tool; hint=工具名不能为空"
    if name in HIGH_RISK_ACTIONS:
        return (
            False,
            f"error=hitl_required; hint=高风险动作 {name!r} 必须人工确认，禁止自动执行",
        )
    if name not in TOOL_WHITELIST:
        return (
            False,
            f"error=not_in_whitelist; hint={name!r} 不在只读白名单 {sorted(TOOL_WHITELIST)}",
        )
    return True, "ok"


def guard_output(text: str) -> GuardResult:
    """调用后 / 出口检查：命中风险短语则改写为安全拒答，不发出原句。"""
    raw = text or ""
    for p in BLOCK_PATTERNS:
        if p in raw:
            return GuardResult(ok=False, text=SAFE_REFUSAL_TEMPLATE, hit_pattern=p)
    return GuardResult(ok=True, text=raw, hit_pattern="")


def should_escalate(
    user_text: str,
    *,
    tool_fails: int = 0,
    pending_action: str = "",
) -> EscalateDecision:
    """流程层：是否暂停自动路径，转人工或 HITL。"""
    text = user_text or ""

    # 1) 用户明确要人工 / 情绪升级词
    for kw in ESCALATE_KEYWORDS:
        if kw in text:
            return EscalateDecision(True, f"用户触发关键词「{kw}」", kind="human")

    # 2) 退款等话术 → HITL（无退款 Tool 或不让自动调）
    refund_cues = ("退款", "给我退", "直接退", "马上退钱")
    if any(c in text for c in refund_cues):
        return EscalateDecision(True, "涉及赔付/退款，需人工确认", kind="hitl_refund")

    # 3) 准备调用的高风险动作名
    action = (pending_action or "").strip()
    if action in HIGH_RISK_ACTIONS:
        return EscalateDecision(
            True, f"pending_action={action} 属高风险", kind="hitl_refund"
        )

    # 4) 工具连续失败
    if tool_fails >= TOOL_FAIL_THRESHOLD:
        return EscalateDecision(
            True,
            f"工具连续失败 {tool_fails} 次 ≥ 阈值 {TOOL_FAIL_THRESHOLD}",
            kind="tool_fails",
        )

    return EscalateDecision(False, "继续自动处理", kind="")


def build_handoff_summary(ctx: SafetyContext) -> str:
    """转人工时附带摘要，避免用户重讲一遍。"""
    lines = [
        f"- session_id: {ctx.session_id}",
        f"- 用户诉求: {ctx.user_text}",
        f"- tool_fails: {ctx.tool_fails}",
    ]
    if ctx.pending_action:
        lines.append(f"- pending_action: {ctx.pending_action}")
    if ctx.trace:
        lines.append("- 最近轨迹:")
        for row in ctx.trace[-5:]:
            tool = row.get("tool") or row.get("action") or "?"
            obs = str(row.get("observation", ""))[:120]
            lines.append(f"  · {tool} → {obs}")
    else:
        lines.append("- 最近轨迹: （尚无 Tool 调用）")
    return "\n".join(lines)


def apply_export_safety(
    draft_reply: str,
    ctx: SafetyContext,
) -> dict[str, Any]:
    """出口统一管线：先判断 escalate/HITL，再跑输出护栏。

    返回字段供 API / demo 使用：
        reply / escalated / hitl / guard_ok / reason / handoff_summary
    """
    decision = should_escalate(
        ctx.user_text,
        tool_fails=ctx.tool_fails,
        pending_action=ctx.pending_action,
    )
    if decision.escalate:
        summary = build_handoff_summary(ctx)
        if decision.kind == "hitl_refund":
            reply = f"{HITL_REFUND_TEMPLATE}\n\n【转人工摘要】\n{summary}"
            return {
                "reply": reply,
                "escalated": True,
                "hitl": True,
                "guard_ok": True,
                "reason": decision.reason,
                "kind": decision.kind,
                "handoff_summary": summary,
                "blocked_auto_tool": True,
            }
        reply = (
            "正在为你转接人工客服，请稍候。"
            f"\n\n【转人工摘要】\n{summary}"
        )
        return {
            "reply": reply,
            "escalated": True,
            "hitl": decision.kind.startswith("hitl"),
            "guard_ok": True,
            "reason": decision.reason,
            "kind": decision.kind,
            "handoff_summary": summary,
            "blocked_auto_tool": False,
        }

    guarded = guard_output(draft_reply)
    return {
        "reply": guarded.text,
        "escalated": False,
        "hitl": False,
        "guard_ok": guarded.ok,
        "reason": (
            f"输出护栏命中「{guarded.hit_pattern}」" if not guarded.ok else "放行"
        ),
        "kind": "guard_block" if not guarded.ok else "pass",
        "handoff_summary": "",
        "blocked_auto_tool": False,
        "hit_pattern": guarded.hit_pattern,
    }
