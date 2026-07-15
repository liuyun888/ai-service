# app/lessons/m07_02_stategraph_basics.py
"""课次 07.02 · StateGraph 基础课包装：Hello + reducer 对照。

把「最小可运行单元」讲清三句话：
1. State 是带类型的共享背包
2. 节点只交回变更字段
3. 列表类字段必须声明 reducer，否则后写覆盖前写
"""

from __future__ import annotations

from typing import Any

from app.graphs.hello_graph import (
    build_hello_graph,
    run_hello,
    run_notes,
    run_notes_overwrite,
)


def demo_hello() -> dict[str, Any]:
    """主示例：hello → HELLO。"""
    app = build_hello_graph()
    # 忘记 compile 时拿到的是 builder，不能 invoke——这里强调返回的已是编译结果
    assert hasattr(app, "invoke"), "必须 compile() 之后才能 invoke"
    final = run_hello("hello graph")
    return {
        "input": {"text": "hello graph"},
        "output": final,
        "lesson": "节点返回 {text: 大写}，合并进 State（默认覆盖同名字段）",
    }


def demo_reducer_append() -> dict[str, Any]:
    """正例：Annotated[list, operator.add] → notes 有两条。"""
    final = run_notes("退货咨询")
    return {
        "output": final,
        "notes_len": len(final.get("notes") or []),
        "lesson": "两条 notes 都还在 → reducer 追加生效",
    }


def demo_reducer_overwrite() -> dict[str, Any]:
    """反例：无 reducer → 只剩后一节点的 notes。"""
    final = run_notes_overwrite("退货咨询")
    return {
        "output": final,
        "notes_len": len(final.get("notes") or []),
        "lesson": "intake 的笔记消失了 → 缺 reducer 时后写覆盖",
    }


def explain_merge() -> list[str]:
    """口头讲解用的要点（写进笔记）。"""
    return [
        "节点返回 dict = 本轮要对 State 做的补丁（partial update）",
        "默认同名字段：后到的值覆盖先到的值",
        "列表要追加：用 Annotated[list, operator.add] 或 add_messages",
        "不要 return 整个旧 State 再改一处——难读且易误伤未改字段",
    ]
