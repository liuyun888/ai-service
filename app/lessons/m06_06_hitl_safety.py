# app/lessons/m06_06_hitl_safety.py
"""课次 06.06 · 把安全边界接到「单 Agent 出口」上的演示编排。

演示三条主路径（默认不调 Chat）：
1. 正常查库存 → 白名单放行 + 输出护栏放行
2. 诱导绝对承诺 → 护栏改写，不发出风险句
3. 直接退款 / 连续 Tool 失败 / 要人工 → HITL 或转人工（带摘要）

高风险退款：白名单里没有 refund Tool；即便有人「准备调用」也会被拦。
"""

from __future__ import annotations

from typing import Any

from app.harness.middleware.safety import (
    TOOL_WHITELIST,
    SafetyContext,
    apply_export_safety,
    check_tool_allowed,
    guard_output,
    should_escalate,
)
from app.tools.inventory import get_inventory


def try_invoke_whitelisted(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """模拟「调用前中间件」：先白名单，再执行（本课只真正执行 get_inventory）。"""
    allowed, reason = check_tool_allowed(tool_name)
    if not allowed:
        return {
            "allowed": False,
            "tool": tool_name,
            "args": args,
            "observation": reason,
            "executed": False,
        }
    if tool_name == "get_inventory":
        obs = str(get_inventory.invoke(args))
        return {
            "allowed": True,
            "tool": tool_name,
            "args": args,
            "observation": obs,
            "executed": True,
        }
    # 白名单内其他 Tool：本课示意「允许但未在此执行」
    return {
        "allowed": True,
        "tool": tool_name,
        "args": args,
        "observation": f"(demo) allowed but skip exec for {tool_name}",
        "executed": False,
    }


def demo_normal_inventory() -> dict[str, Any]:
    """路径 A：正常查库存 → 放行。"""
    user = "EARPHONE-PRO-BK 还有多少件？"
    call = try_invoke_whitelisted("get_inventory", {"sku": "EARPHONE-PRO-BK"})
    draft = (
        f"查过了：{call['observation']}。"
        "以上数字来自库存工具，不是估算。"
    )
    ctx = SafetyContext(
        user_text=user,
        session_id="s-safe-stock",
        tool_fails=0,
        trace=[
            {
                "tool": call["tool"],
                "args": call["args"],
                "observation": call["observation"],
            }
        ],
    )
    out = apply_export_safety(draft, ctx)
    return {"user": user, "tool_call": call, "export": out}


def demo_promise_guard() -> dict[str, Any]:
    """路径 B：模型（或脚本）草稿含绝对承诺 → 护栏拦住。"""
    user = "能不能保证明天一定送到？"
    # 故意写一段「危险草稿」，模拟模型没守 System
    draft = "好的，我们保证明天下午绝对能到，请放心。"
    ctx = SafetyContext(user_text=user, session_id="s-promise")
    # 先看裸护栏，再走出口管线
    bare = guard_output(draft)
    export = apply_export_safety(draft, ctx)
    return {"user": user, "draft": draft, "bare_guard": bare, "export": export}


diagnose_draft = "根据描述，我判断你一定治愈，按这个方子吃就行。"  # 反例草稿


def demo_diagnose_guard() -> dict[str, Any]:
    """对照：诊断式 / 一定治愈 口吻拦截。"""
    user = "我头疼，开点药呗"
    draft = diagnose_draft
    export = apply_export_safety(draft, SafetyContext(user_text=user, session_id="s-med"))
    return {"user": user, "draft": draft, "export": export}


def demo_refund_hitl() -> dict[str, Any]:
    """路径 C：直接退款 → HITL，且 refund Tool 不在白名单。"""
    user = "直接给我退款，别问了"
    # 若 Agent 幻觉要调退款
    blocked = try_invoke_whitelisted("refund", {"order_id": "O999"})
    decision = should_escalate(user)
    ctx = SafetyContext(
        user_text=user,
        session_id="s-refund",
        pending_action="refund",
        trace=[{"tool": "refund", "observation": blocked["observation"]}],
    )
    export = apply_export_safety("（不应发出的自动退款成功话术）", ctx)
    return {
        "user": user,
        "whitelist_block": blocked,
        "decision": decision,
        "export": export,
        "whitelist": sorted(TOOL_WHITELIST),
    }


def demo_tool_fails_escalate() -> dict[str, Any]:
    """连续 Tool 失败 → 转人工 + 摘要。"""
    user = "查一下 NO-SUCH-SKU 到底有没有货"
    fails = []
    for _ in range(2):
        call = try_invoke_whitelisted("get_inventory", {"sku": "NO-SUCH-SKU"})
        fails.append(call)
    # 业务上可把 not_found 计为失败次数（教学简化：连续两次 not_found）
    tool_fails = sum(
        1 for c in fails if "not_found" in str(c.get("observation", ""))
    )
    ctx = SafetyContext(
        user_text=user,
        session_id="s-fails",
        tool_fails=tool_fails,
        trace=[
            {"tool": c["tool"], "args": c["args"], "observation": c["observation"]}
            for c in fails
        ],
    )
    draft = "我再试一次自动查询……"  # 若继续自动会没完没了
    export = apply_export_safety(draft, ctx)
    return {"user": user, "tool_fails": tool_fails, "calls": fails, "export": export}


def demo_ask_human() -> dict[str, Any]:
    """用户明确要人工。"""
    user = "别机器人了，我要投诉，转人工"
    export = apply_export_safety(
        "（不应继续自动废话）",
        SafetyContext(user_text=user, session_id="s-human", tool_fails=0),
    )
    return {"user": user, "export": export}


def run_acceptance_suite() -> dict[str, Any]:
    """课堂打包验收。"""
    return {
        "normal": demo_normal_inventory(),
        "promise": demo_promise_guard(),
        "diagnose": demo_diagnose_guard(),
        "refund": demo_refund_hitl(),
        "tool_fails": demo_tool_fails_escalate(),
        "ask_human": demo_ask_human(),
    }
