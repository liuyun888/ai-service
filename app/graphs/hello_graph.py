# app/graphs/hello_graph.py
"""课次 07.02 · 最小 StateGraph：定义 State → 编译 → invoke。

本文件只做「能跑通的最小单元」，验证：
1. TypedDict 描述共享状态字段
2. 节点只返回「要变更的字段」
3. compile() 之后才能 invoke

扩展：同文件下方的 notes 双节点图，演示 reducer（追加 vs 覆盖）。
下一课再扩成检索→分析→生成流水线。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

# ---------------------------------------------------------------------------
# 1) Hello：单节点回声（课文主示例）
# ---------------------------------------------------------------------------


class HelloState(TypedDict):
    """回声图状态：当前只有一个字段。

    text: 用户输入；经 upper 节点后变为大写。
    """

    text: str


def upper_node(state: HelloState) -> dict[str, Any]:
    """读 State.text → 返回大写；只返回变更字段，不要把整个 state 原样塞回。"""
    raw = state.get("text") or ""
    return {"text": raw.upper()}


def build_hello_graph():
    """组装并编译 Hello 图。

    生命周期：State → StateGraph → add_node → 边 → compile。
    """
    g = StateGraph(HelloState)
    g.add_node("upper", upper_node)
    # 新版 API：START → 节点 → END（等价于旧的 set_entry_point）
    g.add_edge(START, "upper")
    g.add_edge("upper", END)
    return g.compile()


def run_hello(text: str = "hello graph") -> HelloState:
    """调用入口：给小白一个函数就能跑。"""
    app = build_hello_graph()
    out = app.invoke({"text": text})
    return out  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 2) Notes：双节点 + reducer（列表追加，不被后写清空）
# ---------------------------------------------------------------------------


class NotesState(TypedDict, total=False):
    """工单笔记状态：演示「同一字段多人写」时必须声明合并规则。

    title: 普通字段，后写覆盖前写（默认）
    notes: 带 reducer——用 operator.add 做列表拼接（追加）
    """

    title: str
    # Annotated[..., operator.add]：多节点都 return {"notes": [...]} 时拼成一条长列表
    notes: Annotated[list[str], operator.add]


def note_intake_node(state: NotesState) -> dict[str, Any]:
    """节点 A：写下受理笔记。"""
    return {
        "title": state.get("title") or "未命名工单",
        "notes": ["intake: 已登记用户诉求"],
    }


def note_check_node(state: NotesState) -> dict[str, Any]:
    """节点 B：再追加一条审核笔记（靠 reducer，不会把 A 的 notes 冲掉）。"""
    return {"notes": ["check: 材料待人工核验"]}


def build_notes_graph():
    """受理 → 审核 两节点，notes 追加合并。"""
    g = StateGraph(NotesState)
    g.add_node("intake", note_intake_node)
    g.add_node("check", note_check_node)
    g.add_edge(START, "intake")
    g.add_edge("intake", "check")
    g.add_edge("check", END)
    return g.compile()


def run_notes(title: str = "退货咨询") -> NotesState:
    """跑笔记图，观察 notes 是否为两条。"""
    app = build_notes_graph()
    out = app.invoke({"title": title, "notes": []})
    return out  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 3) 反例对照（教学用）：无普通 list，无 reducer → 后写覆盖
# ---------------------------------------------------------------------------


class NotesOverwriteState(TypedDict, total=False):
    """故意不加 reducer：用来对比「notes 被清空」翻车。"""

    title: str
    notes: list[str]


def _intake_overwrite(state: NotesOverwriteState) -> dict[str, Any]:
    return {"title": state.get("title") or "x", "notes": ["intake: 已登记"]}


def _check_overwrite(state: NotesOverwriteState) -> dict[str, Any]:
    # 坏习惯：只返回自己的一条，却把上一节点的 notes 覆盖掉
    return {"notes": ["check: 只有我"]}


def build_notes_overwrite_graph():
    """反例图：不要用在生产。"""
    g = StateGraph(NotesOverwriteState)
    g.add_node("intake", _intake_overwrite)
    g.add_node("check", _check_overwrite)
    g.add_edge(START, "intake")
    g.add_edge("intake", "check")
    g.add_edge("check", END)
    return g.compile()


def run_notes_overwrite(title: str = "退货咨询") -> NotesOverwriteState:
    app = build_notes_overwrite_graph()
    return app.invoke({"title": title, "notes": []})  # type: ignore[return-value]


if __name__ == "__main__":
    # 直接 python app/graphs/hello_graph.py 时的自检（cwd 需在 ai-service）
    print(run_hello("hello graph"))
