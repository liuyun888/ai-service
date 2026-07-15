# app/lessons/m08_04_deep_agents.py
"""课次 08.04 · Deep Agent：售后改进方案（todos + 按需读文件）。

默认离线脚本化 plan/step；USE_CHAT=1 时可用模型写 todos。
"""

from __future__ import annotations

import os
import re
from typing import Any

from app.harness.context.vfs import DEFAULT_VFS, VirtualFS
from app.harness.deep_agent import (
    DeepState,
    Todo,
    all_done,
    run_deep,
    todos_snapshot,
    write_todos,
)

# 主示例目标（与正文一致）
DEMO_GOAL = "根据退货政策与近一周投诉摘要，给一个改进方案大纲。"

# 故意过深的拆解：用来演示 max_steps 截断
TOO_MANY_TITLES = [
    f"微小步骤 {i}: 检查细则 #{i}" for i in range(1, 13)
]


def should_go_deep(task: str) -> dict[str, Any]:
    """粗判：是否值得上 Deep（todos）；反例是 FAQ 类。

    直觉：多证据、多约束、要可恢复进度 → Deep；一问一答 → 普通 Agent。
    """
    t = task or ""
    shallow_hints = ("几天", "多少钱", "是不是", "吗？", "吗?")
    deep_hints = ("方案", "大纲", "改进", "规划", "调研", "对比", "设计")
    if any(h in t for h in deep_hints) and len(t) > 12:
        return {
            "deep": True,
            "reason": "多步证据 + 产出结构化交付，适合显式 todos",
            "counterexample": "退货要几天？→ 单次 read/查库即可，不必 Deep",
        }
    if any(h in t for h in shallow_hints) and "方案" not in t:
        return {
            "deep": False,
            "reason": "短问答/单事实，普通 Agent 更省",
            "counterexample": DEMO_GOAL,
        }
    return {
        "deep": True,
        "reason": "默认偏保守：复杂表述仍走 todos，可用口令关闭",
        "counterexample": "查 SKU-1 库存→ 一次 Tool 够了",
    }


def plan_aftersale(goal: str) -> list[str]:
    """脚本化规划：可验证的 5 步（对齐正文示例）。"""
    _ = goal
    return [
        "read 退货政策关键条款（已拆封/质量问题）",
        "整理投诉摘要中的 Top3 问题",
        "草拟方案大纲（问题→动作→度量）",
        "自检：每条动作能否指回证据路径",
        "输出最终大纲",
    ]


def _read_policy_bits(vfs: VirtualFS) -> str:
    """按需读政策片段（复用 08.03 VFS，不预装全书）。"""
    hits = vfs.search_docs("已拆封")
    path = hits[0]["path"] if hits else "manual/return_policy.md"
    return vfs.read_doc(path, offset=0, limit=700)


def _read_complaints(vfs: VirtualFS) -> str:
    return vfs.read_doc("case/complaints_week.md", offset=0, limit=900)


def step_aftersale(state: DeepState, todo: Todo, *, vfs: VirtualFS | None = None) -> str:
    """按 todo 标题路由：真实读文件或基于已读笔记拼大纲。"""
    fs = vfs or DEFAULT_VFS
    title = todo.title

    if title.startswith("read") or "政策" in title:
        chunk = _read_policy_bits(fs)
        # 塞进 notes 旁白，后续步可「看见」
        state.notes.append(f"[evidence:policy] {chunk[:280]}")
        return "已 read 政策；关键：已拆封通常不支持无理由→走质量问题"

    if "Top3" in title or "投诉" in title:
        chunk = _read_complaints(fs)
        state.notes.append(f"[evidence:complaints] {chunk[:280]}")
        # 抽三行加粗问题标题
        tops = re.findall(r"\*\*(.+?)\*\*", chunk)
        tops = tops[:3] or ["口径冲突", "退款时限", "破损误判"]
        return "Top3=" + " | ".join(tops)

    if "草拟" in title or "大纲" in title and "输出" not in title:
        return (
            "草稿：①统一已拆封话术+营销页对齐；"
            "②退款时效一句话标准；③破损单强制质检通道"
        )

    if "自检" in title:
        # 要求笔记里出现证据痕迹
        blob = "\n".join(state.notes)
        ok_policy = "return_policy" in blob or "已拆封" in blob
        ok_comp = "complaints" in blob or "Top3" in blob or "投诉" in blob
        if ok_policy and ok_comp:
            return "自检通过：动作可指回 policy + complaints 路径"
        return "自检告警：证据不足，需回去补 read"

    if "输出" in title or "最终" in title:
        return (
            "【改进方案大纲】\n"
            "1. 问题：已拆封/七天无理由口径冲突 → 动作：改营销页+客服话术卡 → "
            "度量：相关投诉周环比\n"
            "2. 问题：退款时限不清 → 动作：统一「验货后3个工作日」话术 → "
            "度量：追问工单数\n"
            "3. 问题：破损误走无理由 → 动作：破损拍照模板+质检路由 → "
            "度量：误拒率\n"
            "依据：manual/return_policy.md ；case/complaints_week.md"
        )

    return f"mock done: {title}"


def run_aftersale_deep(*, max_steps: int = 8, vfs: VirtualFS | None = None) -> DeepState:
    """跑主示例：售后改进方案。"""
    fs = vfs or DEFAULT_VFS

    def _step(state: DeepState, todo: Todo) -> str:
        return step_aftersale(state, todo, vfs=fs)

    return run_deep(DEMO_GOAL, plan_aftersale, _step, max_steps=max_steps)


def run_max_steps_demo(*, max_steps: int = 3) -> DeepState:
    """故意拆很多步 + 很小 max_steps，观察截断轨迹。"""

    def plan(_: str) -> list[str]:
        return list(TOO_MANY_TITLES)

    def step(state: DeepState, todo: Todo) -> str:
        return f"done {todo.title}"

    return run_deep("演示 max_steps", plan, step, max_steps=max_steps)


def shallow_dump_outline() -> dict[str, Any]:
    """反面：一把梭长文（无 todos）——对比用。"""
    text = (
        "（浅 Agent 一把梭）先说一堆背景……然后十五条建议……"
        "中间忘了看投诉 Top3……也没引用政策路径……结束。"
    )
    return {
        "mode": "shallow_dump",
        "has_todos": False,
        "chars": len(text),
        "text": text,
        "risk": "中途丢约束、无法从某步续跑、难观测进度",
    }


def plan_with_llm(goal: str) -> list[str]:
    """可选：让模型写出 3～7 条 todo 标题。"""
    from app.models.factory import get_chat_model

    model = get_chat_model(temperature=0.2)
    prompt = (
        "把下面目标拆成 3 到 7 条可验证的 todo，每行一条，不要序号外的废话。\n"
        f"目标：{goal}"
    )
    resp = model.invoke(prompt)
    content = str(getattr(resp, "content", resp) or "")
    lines = []
    for raw in content.splitlines():
        line = raw.strip()
        line = re.sub(r"^[\d一二三四五六七八九十]+[、\.\)．]\s*", "", line)
        line = line.lstrip("-•* ").strip()
        if line:
            lines.append(line)
    return lines[:7] or plan_aftersale(goal)


def run_aftersale_with_llm_plan(*, max_steps: int = 8) -> DeepState:
    """真模型只负责写 todos；步进仍用脚本（省 token、可验收）。"""
    return run_deep(
        DEMO_GOAL,
        plan_with_llm,
        lambda s, t: step_aftersale(s, t),
        max_steps=max_steps,
    )


def demo_suite(*, use_chat: bool | None = None) -> dict[str, Any]:
    """本课一键套件。"""
    if use_chat is None:
        use_chat = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}

    deep = run_aftersale_deep()
    capped = run_max_steps_demo(max_steps=3)
    shallow = shallow_dump_outline()
    gate = should_go_deep(DEMO_GOAL)
    faq_gate = should_go_deep("退货要几天？")

    llm_state = run_aftersale_with_llm_plan() if use_chat else None

    return {
        "use_chat": use_chat,
        "goal": DEMO_GOAL,
        "deep": deep,
        "deep_todos": todos_snapshot(deep),
        "deep_all_done": all_done(deep),
        "capped": capped,
        "capped_pending": [t.title for t in capped.todos if not t.done],
        "shallow": shallow,
        "gate_demo": gate,
        "gate_faq": faq_gate,
        "llm": llm_state,
        "llm_todos": todos_snapshot(llm_state) if llm_state else None,
    }


# 给 REPL 用：手动改 todos 示范
def demo_rewrite_todos() -> DeepState:
    """中途发现新工作 → write_todos 重写列表。"""
    state = DeepState(goal="演示重写 todos")
    write_todos(state, ["A", "B"])
    write_todos(state, ["A 已调整", "B", "C 新增自检"])
    return state
