# app/harness/subagent.py
"""课次 08.05 · 子 Agent 委派：隔离上下文 + 深度限制 + 摘要回收。

工程含义：
- 父：拆任务、定验收、合并
- 子：只拿 brief + 必要附件，默认看不到父的闲聊
- 防套娃：depth 默认最大 1；子不能再 task 子
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.harness.skills.registry import load_brief


@dataclass
class SubagentResult:
    """子 Agent 回收结果（只回摘要/结构化，不回整段思维链）。"""

    skill: str
    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    # 调试用：实际喂给子的消息条数（应远小于父会话）
    child_message_count: int = 0
    error: str = ""


# 可调：父级最多同时/累计派几个子（演示用累计）
DEFAULT_MAX_CHILDREN = 4
# 可调：委派深度；1 = 子不能再开子
DEFAULT_MAX_DEPTH = 1


@dataclass
class DelegateBudget:
    """防止套娃与爆炸的预算。"""

    max_depth: int = DEFAULT_MAX_DEPTH
    max_children: int = DEFAULT_MAX_CHILDREN
    children_used: int = 0


Handler = Callable[[str, dict[str, Any]], dict[str, Any]]


def run_subagent(
    skill: str,
    *,
    attachments: dict[str, Any] | None = None,
    parent_messages: list[Any] | None = None,
    depth: int = 0,
    budget: DelegateBudget | None = None,
    handler: Handler | None = None,
    allow_nested: bool = False,
) -> SubagentResult:
    """派一个子 Agent：新上下文 = brief + attachments，不拷贝父闲聊。

    参数:
        skill: 注册表中的名字
        attachments: 显式传入的材料（JSON/路径等）
        parent_messages: 仅用于对比演示；默认 **不会** 喂给子
        depth: 当前深度（父调子 = 0→1）
        budget: 并发/累计子任务上限
        handler: 实际干活的函数；None 则报错（由 lesson 注入）
        allow_nested: 是否允许子再委派（默认 False）

    返回:
        SubagentResult
    """
    budget = budget or DelegateBudget()
    attachments = dict(attachments or {})

    if depth >= budget.max_depth and not allow_nested:
        return SubagentResult(
            skill=skill,
            ok=False,
            summary="",
            error=f"error=depth_exceeded:{depth}>={budget.max_depth}",
        )
    if budget.children_used >= budget.max_children:
        return SubagentResult(
            skill=skill,
            ok=False,
            summary="",
            error=f"error=max_children:{budget.max_children}",
        )

    try:
        brief = load_brief(skill)
    except KeyError as exc:
        return SubagentResult(skill=skill, ok=False, summary="", error=str(exc))

    # 隔离：只组装 brief + 附件；刻意忽略 parent_messages
    child_messages = [
        {"role": "system", "content": brief},
        {"role": "user", "content": f"attachments={attachments}"},
    ]
    leaked = False
    if parent_messages:
        # 验收用：确认我们没有把父消息拼进去
        joined = str(child_messages)
        for m in parent_messages:
            blob = str(m)
            if blob and blob in joined and "闲聊污染探针" in blob:
                leaked = True

    budget.children_used += 1
    if handler is None:
        return SubagentResult(
            skill=skill,
            ok=False,
            summary="",
            child_message_count=len(child_messages),
            error="error=no_handler",
        )

    try:
        data = handler(brief, attachments)
    except Exception as exc:  # noqa: BLE001
        return SubagentResult(
            skill=skill,
            ok=False,
            summary="",
            child_message_count=len(child_messages),
            error=f"{type(exc).__name__}: {exc}",
        )

    summary = str(data.get("summary") or "")[:500]
    return SubagentResult(
        skill=skill,
        ok=True,
        summary=summary,
        data={k: v for k, v in data.items() if k != "summary"},
        child_message_count=len(child_messages),
        error="leak_detected" if leaked else "",
    )


def polish_with_pref(draft: str, pref: str | None) -> str:
    """父合并阶段：按记忆中的偏好润色（演示规则）。

    只做轻量改写：去绝对化承诺、标明「来自记忆」；不重排整篇结构。
    """
    text = draft or ""
    tag = "（来自记忆的偏好已应用）" if pref else "（无记忆偏好）"
    if not pref:
        return f"{text}\n\n{tag}"
    if "少形容词" in pref or "避免" in pref or "绝对" in pref:
        for bad in ("非常完美", "绝对", "一定赔付", "保证全额"):
            text = text.replace(bad, "（已按偏好去掉绝对化表述）")
    # 条目制：若草稿还是大段散文且无编号，才提醒（本课 writer 已是条目）
    if "条目" in pref and not any(ln.strip()[:2].rstrip(".").isdigit() for ln in text.splitlines() if ln.strip()):
        text = "（已按偏好改为条目制）\n" + text
    return f"{text}\n\n> 来自记忆的偏好：{pref}\n{tag}"
