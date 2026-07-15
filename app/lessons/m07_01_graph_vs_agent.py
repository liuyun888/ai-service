# app/lessons/m07_01_graph_vs_agent.py
"""课次 07.01 · 图 vs 单 Agent：选型清单 + 对照实验。

本课要建立的心智：
- 单 Agent Loop：适合 FAQ、短任务、少分支
- 状态图：阶段钉死、要 HITL、要可测路由时再上
- 别凡是 AI 都上图

对照：
- FAQ「退货几天」→ Agent 短链路（甚至可一步 Tool）
- 「我要退货 ORD123」→ 轻量图：classify→校验→等人→开单草稿
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.graphs.return_lite import run_return_lite
from app.tools.inventory import get_inventory
from app.tools.knowledge import search_knowledge

# ---------------------------------------------------------------------------
# 选型清单（建议打印贴墙；勾选 ≥2 再上图）
# ---------------------------------------------------------------------------

CRITERIA: list[tuple[str, str]] = [
    ("staged", "存在明确业务阶段（受理→审核→通知），不能乱跳"),
    ("hitl", "需要人工确认后才能继续"),
    ("resume", "流程可能中断数分钟～数天再续跑"),
    ("routable", "不同意图必须走不同子系统，且要可测"),
    ("audit", "需要多角色分工且交接状态要审计"),
]

Decision = Literal["Agent", "Graph", "先 Agent 后升级"]


@dataclass
class ScenarioScore:
    """一个产品场景的选型结果。"""

    name: str
    flags: dict[str, bool]
    decision: Decision
    why: str

    @property
    def hits(self) -> int:
        return sum(1 for v in self.flags.values() if v)


def decide(flags: dict[str, bool]) -> tuple[Decision, str]:
    """勾选条数 → 结论。

    ≥2 条上图信号 → Graph；1 条 → 先 Agent 后升级；0 → Agent。
    """
    n = sum(1 for v in flags.values() if v)
    if n >= 2:
        return "Graph", f"命中 {n} 条上图信号（≥2）"
    if n == 1:
        return "先 Agent 后升级", "仅 1 条信号：先跑通 Agent，别一上来全站上图"
    return "Agent", "无线上图硬需求：单 Agent Loop 足够"


# 预置 5 个场景（课堂可改成自己产品）
DEMO_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "包装尺寸 FAQ",
        "flags": {
            "staged": False,
            "hitl": False,
            "resume": False,
            "routable": False,
            "audit": False,
        },
    },
    {
        "name": "查实时库存",
        "flags": {
            "staged": False,
            "hitl": False,
            "resume": False,
            "routable": False,
            "audit": False,
        },
    },
    {
        "name": "退货审核（校验→判责→人确认→开单）",
        "flags": {
            "staged": True,
            "hitl": True,
            "resume": True,
            "routable": True,
            "audit": True,
        },
    },
    {
        "name": "请假审批流",
        "flags": {
            "staged": True,
            "hitl": True,
            "resume": True,
            "routable": False,
            "audit": True,
        },
    },
    {
        "name": "异常理赔确认",
        "flags": {
            "staged": True,
            "hitl": True,
            "resume": False,
            "routable": True,
            "audit": False,
        },
    },
]


def score_scenarios(
    scenarios: list[dict[str, Any]] | None = None,
) -> list[ScenarioScore]:
    """批量打选型表。"""
    rows: list[ScenarioScore] = []
    for s in scenarios or DEMO_SCENARIOS:
        flags = dict(s["flags"])
        decision, why = decide(flags)
        rows.append(
            ScenarioScore(name=s["name"], flags=flags, decision=decision, why=why)
        )
    return rows


def run_faq_as_agent(question: str) -> dict[str, Any]:
    """单 Agent 心智：没有显式阶段图，一步（或短 Loop）查知识就答。"""
    obs = str(search_knowledge.invoke({"query": question}))
    if obs == "not_found":
        answer = "知识库未命中；单 Agent 路径下可拒答或追问。"
    else:
        answer = f"根据政策检索：{obs}"
    return {
        "mode": "single_agent",
        "question": question,
        "trace": [{"tool": "search_knowledge", "observation": obs}],
        "answer": answer,
        "path": ["think", "act:search_knowledge", "final"],
        "lesson": "FAQ 无审批暂停需求 → 不必上图",
    }


def run_stock_as_agent(sku: str = "EARPHONE-PRO-BK") -> dict[str, Any]:
    """对照：查库存同样是单 Agent 够用。"""
    obs = str(get_inventory.invoke({"sku": sku}))
    return {
        "mode": "single_agent",
        "trace": [{"tool": "get_inventory", "observation": obs}],
        "answer": f"查过了：{obs}",
        "path": ["think", "act:get_inventory", "final"],
    }


def run_return_as_graph(user_text: str) -> dict[str, Any]:
    """状态图路径：阶段写在边上，path 可回放。"""
    state = run_return_lite(user_text)
    return {
        "mode": "state_graph",
        "user_text": user_text,
        "intent": state.get("intent"),
        "path": state.get("path") or [],
        "needs_human": bool(state.get("needs_human")),
        "answer": state.get("answer") or "",
        "order_id": state.get("order_id") or "",
        "lesson": "退货多阶段 + 要人工确认 → 图更合适",
    }


def contrast_pair() -> dict[str, Any]:
    """同一模块里两道题：FAQ 走 Agent，退货走图。"""
    faq = run_faq_as_agent("退货几天内可以？")
    ret = run_return_as_graph("我要退货，订单号 ORD12345")
    return {"faq_agent": faq, "return_graph": ret}
