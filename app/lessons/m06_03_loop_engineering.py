# app/lessons/m06_03_loop_engineering.py
"""课次 06.03 · Loop Engineering：Think → Act → Observe 可约束循环。

本课三件事（对照实验，默认不调 Chat）：
1. 打印完整轨迹（Thought / Action / Observation）
2. max_steps 刹车 + 步数用尽兜底话术
3. 重复调用检测：相同 Tool+相同参数连打 → 打断

和 05.07 `run_tool_agent` 的关系：那边是「最小能跑」；
这里把刹车与可观测做成显式工程旋钮，方便你抄到生产。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from app.tools.inventory import get_inventory, get_shipment

# ---------------------------------------------------------------------------
# 可调旋钮（改了会影响演示行为——注释写清给小白）
# ---------------------------------------------------------------------------

# 整次任务最多走几圈循环；防止空转烧钱 / 账单爆炸
DEFAULT_MAX_STEPS = 6

# 同一「工具名 + 参数」连续出现几次就强制打断（重复无效调用）
DEFAULT_MAX_IDENTICAL = 2

# 工具目录：本课只复用 05.07 两个只读 Tool
TOOL_CATALOG: dict[str, Any] = {
    "get_inventory": get_inventory,
    "get_shipment": get_shipment,
}


@dataclass
class Decision:
    """某一步「想清楚」之后的决定：要么调工具，要么直接收工。"""

    kind: Literal["act", "final"]
    thought: str
    tool: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    final_answer: str = ""


@dataclass
class LoopContext:
    """循环里能看见的上下文：步数、已有轨迹、最近一次观察。"""

    goal: str
    step: int
    trace: list[dict[str, Any]]
    last_observation: str | None = None


DecideFn = Callable[[LoopContext], Decision]


def _call_signature(tool: str, args: dict[str, Any]) -> str:
    """把工具调用压成可比较的签名字符串，用于重复检测。"""
    # 排序键 → 参数顺序不影响「是否相同调用」的判断
    items = ",".join(f"{k}={args[k]!r}" for k in sorted(args.keys()))
    return f"{tool}({items})"


def _invoke_tool(tool: str, args: dict[str, Any]) -> str:
    """执行 Tool；未知工具也返回可读错误字符串（回灌 Observation，不要吞掉）。"""
    fn = TOOL_CATALOG.get(tool)
    if fn is None:
        return f"error: unknown tool {tool!r}"
    try:
        return str(fn.invoke(args))
    except Exception as exc:  # noqa: BLE001 — 教学：原始错误留给下一步 Thought
        return f"error: {type(exc).__name__}: {exc}"


def run_tao_loop(
    goal: str,
    decide: DecideFn,
    *,
    max_steps: int = DEFAULT_MAX_STEPS,
    max_identical: int = DEFAULT_MAX_IDENTICAL,
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """显式 Think → Act → Observe 循环（教学版 Loop Engineering）。

    参数:
        goal: 用户目标（一句话任务）
        decide: 策略函数——真实系统里往往是「绑了 tools 的模型」；这里可脚本化
        max_steps: 步数上限（刹车）
        max_identical: 相同调用连续上限；<=0 表示关闭重复检测
        on_step: 每步回调，方便 demo 脚本打印

    返回:
        answer / trace / stop_reason / steps 等，便于断言与写笔记
    """
    trace: list[dict[str, Any]] = []
    last_obs: str | None = None
    # 连续相同调用计数（例如同一坏 sku 连打）
    identical_streak = 0
    last_sig: str | None = None

    for step in range(1, max_steps + 1):
        ctx = LoopContext(
            goal=goal,
            step=step,
            trace=list(trace),
            last_observation=last_obs,
        )
        decision = decide(ctx)

        if decision.kind == "final":
            row = {
                "step": step,
                "thought": decision.thought,
                "action": None,
                "args": {},
                "observation": None,
                "event": "final",
            }
            trace.append(row)
            if on_step:
                on_step(row)
            return {
                "goal": goal,
                "answer": decision.final_answer,
                "trace": trace,
                "steps": step,
                "stop_reason": "final",
                "max_steps": max_steps,
            }

        # ---- Act：调工具 ----
        sig = _call_signature(decision.tool, decision.args)
        if max_identical > 0 and last_sig is not None and sig == last_sig:
            identical_streak += 1
        else:
            identical_streak = 1
            last_sig = sig

        # 重复检测闸门：在真正第 N+1 次之前就打断（第 N 次已执行过）
        if max_identical > 0 and identical_streak > max_identical:
            row = {
                "step": step,
                "thought": decision.thought,
                "action": decision.tool,
                "args": dict(decision.args),
                "observation": None,
                "event": "duplicate_stop",
                "signature": sig,
                "identical_streak": identical_streak,
            }
            trace.append(row)
            if on_step:
                on_step(row)
            answer = (
                f"检测到重复无效调用（连续>{max_identical} 次相同：{sig}）。"
                "已打断循环。请核对参数或转人工，勿空转烧钱。"
            )
            return {
                "goal": goal,
                "answer": answer,
                "trace": trace,
                "steps": step,
                "stop_reason": "duplicate_stop",
                "max_steps": max_steps,
                "blocked_signature": sig,
            }

        obs = _invoke_tool(decision.tool, decision.args)
        last_obs = obs
        row = {
            "step": step,
            "thought": decision.thought,
            "action": decision.tool,
            "args": dict(decision.args),
            "observation": obs,
            "event": "act",
            "signature": sig,
        }
        trace.append(row)
        if on_step:
            on_step(row)

    # ---- 步数用尽兜底：别假装成功，把已查到的事实摊开 ----
    facts = [
        f"- {t['action']}({t['args']}) → {t['observation']}"
        for t in trace
        if t.get("event") == "act"
    ]
    facts_block = "\n".join(facts) if facts else "- （本轮尚未拿到任何 Observation）"
    answer = (
        f"步数已用尽（max_steps={max_steps}）。我查到的信息如下：\n"
        f"{facts_block}\n"
        "如需继续请缩小问题或转人工。"
    )
    return {
        "goal": goal,
        "answer": answer,
        "trace": trace,
        "steps": max_steps,
        "stop_reason": "max_steps",
        "max_steps": max_steps,
    }


# ---------------------------------------------------------------------------
# 三种脚本化策略：幸福路径 / 会死磕 / 故意拖到刹车
# ---------------------------------------------------------------------------


def policy_happy_path(ctx: LoopContext) -> Decision:
    """幸福路径：库存 → 运单 → Final（两工具两类 Observation）。"""
    done_tools = {t["action"] for t in ctx.trace if t.get("event") == "act"}

    if "get_inventory" not in done_tools:
        return Decision(
            kind="act",
            thought="目标含库存查询，先确认 sku 再调用 get_inventory",
            tool="get_inventory",
            args={"sku": "EARPHONE-PRO-BK"},
        )
    if "get_shipment" not in done_tools:
        return Decision(
            kind="act",
            thought="库存已拿到；下一步查运单 SF123456，禁止编 ETA",
            tool="get_shipment",
            args={"tracking_no": "SF123456"},
        )

    inv = next(
        (t["observation"] for t in ctx.trace if t.get("action") == "get_inventory"),
        "",
    )
    ship = next(
        (t["observation"] for t in ctx.trace if t.get("action") == "get_shipment"),
        "",
    )
    return Decision(
        kind="final",
        thought="两段 Observation 齐全，汇总回答，不编造物流时效",
        final_answer=(
            f"根据工具结果：库存侧 {inv}；物流侧 {ship}。"
            "以上均来自 Observation，不是模型估算。"
        ),
    )


def policy_dead_repeat(ctx: LoopContext) -> Decision:
    """故障策略：永远对坏 sku 调 get_inventory（用来演示重复检测）。"""
    return Decision(
        kind="act",
        thought="（错误）看到 not_found 仍打算用同一坏参数再查一遍",
        tool="get_inventory",
        args={"sku": "NO-SUCH-SKU"},
    )


def policy_never_final(ctx: LoopContext) -> Decision:
    """故障策略：每次换不同 sku 查库存却从不 Final（用来演示 max_steps 刹车）。"""
    # 故意每次参数不同 → 重复检测不会拦，只能靠 max_steps
    skus = ["EARPHONE-PRO-BK", "EARPHONE-PRO-WH", "CABLE-USB-C", "EARPHONE-PRO-BK", "EARPHONE-PRO-WH", "CABLE-USB-C"]
    idx = min(ctx.step - 1, len(skus) - 1)
    sku = skus[idx]
    return Decision(
        kind="act",
        thought=f"（拖延）再查一次库存 sku={sku}，迟迟不给出 Final Answer",
        tool="get_inventory",
        args={"sku": sku},
    )


def demo_happy_path(*, max_steps: int = DEFAULT_MAX_STEPS) -> dict[str, Any]:
    """STEP：正常两工具轨迹，stop_reason=final。"""
    return run_tao_loop(
        "查黑耳机库存，并查运单 SF123456，再解释（勿编 ETA）",
        policy_happy_path,
        max_steps=max_steps,
        max_identical=DEFAULT_MAX_IDENTICAL,
    )


def demo_duplicate_brake(*, max_identical: int = DEFAULT_MAX_IDENTICAL) -> dict[str, Any]:
    """STEP：同一坏调用连打 → duplicate_stop。"""
    return run_tao_loop(
        "查一个不存在的 SKU（演示重复检测）",
        policy_dead_repeat,
        max_steps=10,  # 故意给够大，证明是重复检测停的，不是步数
        max_identical=max_identical,
    )


def demo_max_steps_brake(*, max_steps: int = 3) -> dict[str, Any]:
    """STEP：从不 Final → 撞上 max_steps 兜底。"""
    return run_tao_loop(
        "故意拖延、永不收工（演示步数刹车）",
        policy_never_final,
        max_steps=max_steps,
        max_identical=0,  # 关闭重复检测，只看步数上限
    )


def format_trace_lines(trace: list[dict[str, Any]]) -> list[str]:
    """把轨迹格式化成可读行（Thought / Action / Observation）。"""
    lines: list[str] = []
    for t in trace:
        step = t.get("step")
        lines.append(f"--- STEP {step} · {t.get('event')} ---")
        lines.append(f"Thought: {t.get('thought')}")
        if t.get("action"):
            lines.append(f"Action:  {t['action']}({t.get('args')})")
        if t.get("observation") is not None:
            lines.append(f"Observe: {t['observation']}")
        if t.get("event") == "duplicate_stop":
            lines.append(f"Brake:   重复调用打断 · {t.get('signature')}")
        if t.get("event") == "final":
            lines.append("Event:   Final Answer（退出循环）")
    return lines
