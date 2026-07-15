# app/graphs/checkpointing.py
"""课次 07.05 · Checkpointer：按 thread_id 持久化 State，支持续跑。

本课先确认机制本身（MemorySaver）；真 HITL interrupt 留给 07.06。

关键心智：
- thread_id = 钥匙；同 id 续写，换 id 新故事
- compile(..., checkpointer=MemorySaver())
- 二次 invoke 时：不要把「会覆盖历史」的字段又塞成初始值
  推荐续跑：app.invoke({}, config) 或只传本轮要更新的字段
- 用 get_state(config) 验收「读到了历史快照」
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

# ---------------------------------------------------------------------------
# 可调：开发用内存；生产务必换外部存储（本课只演示接口形状）
# ---------------------------------------------------------------------------

# True：每次 build 共用模块级 saver，便于「进程内」多次调用对照
# 注意：MemorySaver 重启进程即丢，不能直接上生产
_SHARED_MEMORY: MemorySaver | None = None


def get_memory_saver(*, fresh: bool = False) -> MemorySaver:
    """拿一个 Checkpointer。

    fresh=True 时新建（测隔离很方便）；默认复用模块级实例。
    """
    global _SHARED_MEMORY
    if fresh or _SHARED_MEMORY is None:
        _SHARED_MEMORY = MemorySaver()
    return _SHARED_MEMORY


class CPState(TypedDict, total=False):
    """计数续跑状态。

    count: 普通字段，后写覆盖（续跑时勿再传 0 把历史冲掉）
    log: 追加列表，演示 reducer + checkpoint 一起留下足迹
    """

    count: int
    log: Annotated[list[str], operator.add]


def inc_node(state: CPState) -> dict[str, Any]:
    """每跑一轮：count+1，并往 log 追加一行。"""
    c = int(state.get("count") or 0) + 1
    return {"count": c, "log": [f"count={c}"]}


def build_cp_graph(*, checkpointer: MemorySaver | None = None, fresh_memory: bool = False):
    """编译带 Checkpointer 的最小图：START → inc → END。"""
    g = StateGraph(CPState)
    g.add_node("inc", inc_node)
    g.add_edge(START, "inc")
    g.add_edge("inc", END)
    saver = checkpointer or get_memory_saver(fresh=fresh_memory)
    return g.compile(checkpointer=saver), saver


def thread_config(thread_id: str) -> dict[str, Any]:
    """组装 LangGraph 要求的 config。"""
    return {"configurable": {"thread_id": thread_id}}


def run_first(thread_id: str, *, app=None) -> dict[str, Any]:
    """同一线程的第一枪：带初始 State。"""
    if app is None:
        app, _ = build_cp_graph()
    cfg = thread_config(thread_id)
    out = app.invoke({"count": 0, "log": []}, cfg)
    snap = app.get_state(cfg)
    return {"output": out, "values": dict(snap.values), "config": cfg, "app": app}


def run_resume(app, thread_id: str) -> dict[str, Any]:
    """续跑：空补丁，从 checkpoint 接着 +1（不要再传 count=0）。"""
    cfg = thread_config(thread_id)
    out = app.invoke({}, cfg)
    snap = app.get_state(cfg)
    return {"output": out, "values": dict(snap.values)}


def run_wrong_overwrite(app, thread_id: str) -> dict[str, Any]:
    """反例：又传 count=0，会把历史计数冲掉再 +1（看起来像没续上）。"""
    cfg = thread_config(thread_id)
    out = app.invoke({"count": 0}, cfg)
    snap = app.get_state(cfg)
    return {"output": out, "values": dict(snap.values), "lesson": "勿用初始值覆盖 checkpoint"}


def get_values(app, thread_id: str) -> dict[str, Any]:
    """只读快照。"""
    snap = app.get_state(thread_config(thread_id))
    return dict(snap.values)


if __name__ == "__main__":
    app, _ = build_cp_graph(fresh_memory=True)
    tid = "demo-1"
    print("first ", run_first(tid, app=app)["values"])
    print("resume", run_resume(app, tid)["values"])
    print("other ", run_first("demo-2", app=app)["values"])
    print("demo-1 again", get_values(app, "demo-1"))
