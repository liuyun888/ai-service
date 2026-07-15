# app/harness/deep_agent.py
"""课次 08.04 · 最小自建 Deep Agent：显式 todos + 步进循环。

直觉：复杂任务别「一次倒万字」；先写可勾选待办，每次只推一条。
不绑特定商业 Deep Agents 框架——能力模型对齐即可验收。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Todo:
    """一条可验证的待办。

    参数:
        id: 从 1 开始的序号
        title: 可验收的动作描述（别写「完成整个项目」）
        done: 是否勾选完成
    """

    id: int
    title: str
    done: bool = False


@dataclass
class DeepState:
    """Deep Agent 运行态：目标、待办、过程笔记、轨迹。

    参数:
        goal: 用户目标一句话
        todos: 当前待办列表（可中途 write 重写）
        notes: 每步产出摘要
        trajectory: 可观测事件（规划 / 步进 / 截断）
        max_steps: 步进上限；改小更容易触发截断演示
    """

    goal: str
    todos: list[Todo] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    max_steps: int = 8
    steps_used: int = 0


PlanFn = Callable[[str], list[str]]
StepFn = Callable[[DeepState, Todo], str]


def write_todos(state: DeepState, titles: list[str]) -> list[Todo]:
    """用新标题列表整体重写待办（规划或发现新工作时调用）。

    参数:
        state: 运行态
        titles: 3～7 条为佳；会重新编号

    返回:
        写好后的 todos
    """
    cleaned = [t.strip() for t in titles if (t or "").strip()]
    state.todos = [Todo(i + 1, t) for i, t in enumerate(cleaned)]
    state.trajectory.append(
        {
            "event": "write_todos",
            "titles": [t.title for t in state.todos],
            "count": len(state.todos),
        }
    )
    return state.todos


def mark_done(state: DeepState, todo_id: int, note: str = "") -> None:
    """把指定 todo 勾为完成，并记一条笔记。"""
    for t in state.todos:
        if t.id == todo_id:
            t.done = True
            detail = note or t.title
            state.notes.append(f"todo#{todo_id}: {detail}")
            state.trajectory.append(
                {
                    "event": "mark_done",
                    "todo_id": todo_id,
                    "title": t.title,
                    "note": detail,
                }
            )
            return
    state.trajectory.append(
        {"event": "mark_done_miss", "todo_id": todo_id, "error": "not_found"}
    )


def pending(state: DeepState) -> list[Todo]:
    """尚未完成的待办。"""
    return [t for t in state.todos if not t.done]


def all_done(state: DeepState) -> bool:
    """是否全部勾选。"""
    return bool(state.todos) and all(t.done for t in state.todos)


def todos_snapshot(state: DeepState) -> list[dict[str, Any]]:
    """便于打印/写笔记的 todos 快照。"""
    return [
        {"id": t.id, "title": t.title, "done": t.done, "status": "done" if t.done else "todo"}
        for t in state.todos
    ]


def run_deep(
    goal: str,
    plan_fn: PlanFn,
    step_fn: StepFn,
    *,
    max_steps: int = 8,
) -> DeepState:
    """先规划再执行：write_todos → 逐条 step → mark_done。

    参数:
        goal: 用户目标
        plan_fn: 根据 goal 返回标题列表
        step_fn: 对单条 Todo 产出一段过程笔记（可调工具/读文件）
        max_steps: 最多推进几条；到了就停，防止 Deep 失控

    返回:
        填满轨迹的 DeepState
    """
    state = DeepState(goal=goal, max_steps=max_steps)
    titles = plan_fn(goal)
    write_todos(state, titles)

    # 只推进「当前未完成」；允许 step_fn 内部再 write_todos 追加工作
    guard = 0
    while pending(state):
        if state.steps_used >= state.max_steps:
            state.notes.append("max_steps reached")
            state.trajectory.append(
                {
                    "event": "max_steps",
                    "steps_used": state.steps_used,
                    "max_steps": state.max_steps,
                    "pending": [t.title for t in pending(state)],
                }
            )
            break
        todo = pending(state)[0]
        note = step_fn(state, todo)
        mark_done(state, todo.id, note=note)
        state.steps_used += 1
        guard += 1
        if guard > state.max_steps + len(state.todos) + 5:
            # 防止 step_fn 疯狂重写 todos 导致死循环
            state.notes.append("guard_break: possible infinite replan")
            state.trajectory.append({"event": "guard_break"})
            break

    state.trajectory.append(
        {
            "event": "finish",
            "all_done": all_done(state),
            "steps_used": state.steps_used,
            "todos": todos_snapshot(state),
        }
    )
    return state
