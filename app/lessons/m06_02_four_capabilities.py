# app/lessons/m06_02_four_capabilities.py
"""课次 06.02 · Agent 四能力：规划 / 工具 / 记忆 / 反思。

检查清单心智：
- 缺规划 → 乱序、漏步骤
- 缺工具 → 只能空谈
- 缺记忆 → 反复问、丢上下文
- 缺反思 → 同一坏参数死磕

本课用「对照实验」让故障可跑出来，再对照填表——不只抄定义。
复用 05.07 Tool；不在这里上完整 Loop 工程（留给 06.03）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.tools.inventory import get_inventory, get_shipment

# ---------------------------------------------------------------------------
# 对照表：针对 05.07 库存 Agent 的「有/弱/无」审计（示例答案，笔记可改）
# ---------------------------------------------------------------------------

AUDIT_05_07_INVENTORY_AGENT: list[dict[str, str]] = [
    {
        "能力": "规划",
        "我的场景表现": "用户问库存时先选 get_inventory，再组织话术",
        "当前实现": "隐式：模型+ReAct 自选下一步（无显式 todo）",
        "缺口": "复杂多目标时易漏步；未强制「先确认 sku 再查」",
    },
    {
        "能力": "工具",
        "我的场景表现": "能拿到真实 mock 库存数字",
        "当前实现": "get_inventory / get_shipment（@tool）",
        "缺口": "尚无 get_order；政策类应接检索 Tool",
    },
    {
        "能力": "记忆",
        "我的场景表现": "单轮 messages 里能看见上一轮 Tool 结果",
        "当前实现": "进程内 messages 列表（会话级）",
        "缺口": "跨请求未落 Redis/摘要；用户偏好未结构化",
    },
    {
        "能力": "反思",
        "我的场景表现": "看到 not_found 时，理想应换策略而不是盲重试",
        "当前实现": "主要靠模型读 Observation（代码层未强制）",
        "缺口": "缺代码闸门：同一坏 sku 仍可能被连调多次",
    },
]


@dataclass
class MemoryScratch:
    """超简短记忆：只记用户已确认的 sku / 运单号（教学用）。"""

    sku: str = ""
    tracking_no: str = ""
    notes: list[str] = field(default_factory=list)

    def remember_sku(self, sku: str) -> None:
        self.sku = (sku or "").strip().upper()
        self.notes.append(f"记住 sku={self.sku}")

    def remember_tracking(self, no: str) -> None:
        self.tracking_no = (no or "").strip().upper()
        self.notes.append(f"记住 tracking_no={self.tracking_no}")


def demo_missing_reflection(*, bad_sku: str = "NO-SUCH-SKU", times: int = 5) -> dict[str, Any]:
    """缺反思：对同一 not_found 结果死磕调用 N 次（故障演示）。"""
    calls: list[str] = []
    for _ in range(times):
        obs = get_inventory.invoke({"sku": bad_sku})
        calls.append(obs)
    return {
        "scenario": "缺反思",
        "fault": f"对 {bad_sku} 连续调用 {times} 次，观察值不变仍死磕",
        "observations": calls,
        "all_not_found": all(c == "not_found" for c in calls),
        "lesson": "缺反思 → 重复无效调用；应停下来换参或请用户重输",
    }


def demo_with_reflection(*, bad_sku: str = "NO-SUCH-SKU") -> dict[str, Any]:
    """有反思：一次 not_found 后立刻换策略（拒答/请重输），不再连调。"""
    obs = get_inventory.invoke({"sku": bad_sku})
    if obs == "not_found":
        # 代码层反思闸门（比「指望模型自觉」更硬）
        return {
            "scenario": "有反思",
            "observation": obs,
            "decision": "stop_and_ask_user",
            "answer": (
                f"SKU「{bad_sku}」查无（not_found）。"
                "请核对编码后重试，我不会再对同一坏参数连打接口。"
            ),
            "extra_calls": 0,
            "lesson": "用 Observation 驱动分支：换策略或停下，而不是死循环",
        }
    return {
        "scenario": "有反思",
        "observation": obs,
        "decision": "answer_with_fact",
        "answer": obs,
        "extra_calls": 0,
        "lesson": "命中则作答",
    }


def demo_memory_two_turns() -> dict[str, Any]:
    """记忆：第一轮提供 sku；第二轮只说「还有货吗」——靠短记忆补全。"""
    mem = MemoryScratch()
    turn1_user = "我的 sku 是 EARPHONE-PRO-BK"
    mem.remember_sku("EARPHONE-PRO-BK")

    turn2_user = "还有货吗？给准确数字。"
    # 无记忆时第二轮缺少 sku → 无法查
    without_memory = "无法查询：未提供 sku（模拟失忆客服）"
    # 有记忆：自动带上上一轮 sku
    obs = get_inventory.invoke({"sku": mem.sku})
    with_memory = f"根据你刚才提供的 {mem.sku}：{obs}"

    return {
        "scenario": "记忆对照",
        "turn1": turn1_user,
        "turn2": turn2_user,
        "memory": {"sku": mem.sku, "notes": list(mem.notes)},
        "without_memory_answer": without_memory,
        "with_memory_answer": with_memory,
        "lesson": "短记忆保留中间结果（sku），避免反复盘问",
    }


def demo_planning_two_steps() -> dict[str, Any]:
    """规划：目标「查黑耳机库存，并查运单 SF123456」拆成两步再汇总。"""
    plan = [
        "1) 确认商品 sku → get_inventory",
        "2) 确认运单号 → get_shipment",
        "3) 汇总两段 Observation，禁止编造",
    ]
    steps_done: list[dict[str, str]] = []

    sku = "EARPHONE-PRO-BK"
    inv = get_inventory.invoke({"sku": sku})
    steps_done.append({"step": "get_inventory", "args": sku, "observation": inv})

    tracking = "SF123456"
    ship = get_shipment.invoke({"tracking_no": tracking})
    steps_done.append({"step": "get_shipment", "args": tracking, "observation": ship})

    summary = (
        f"规划执行完毕：库存侧 {inv}；物流侧 {ship}。"
        "两步按顺序完成，没有跳过查库直接瞎报数。"
    )
    return {
        "scenario": "规划",
        "plan": plan,
        "steps_done": steps_done,
        "summary": summary,
        "lesson": "把目标拆成可执行步骤；每步对应一个 Tool",
    }


def classify_fault(symptom: str) -> str:
    """把故障话术粗归到「缺某能力」（笔记练习用）。"""
    s = symptom.strip()
    rules = [
        ("死循环", "反思"),
        ("重复无效", "反思"),
        ("not_found 还一直调", "反思"),
        ("越查", "反思"),
        ("乱序", "规划"),
        ("漏步", "规划"),
        ("该先查", "规划"),
        ("直接编", "规划"),
        ("空谈", "工具"),
        ("从不调工具", "工具"),
        ("瞎编库存", "工具"),
        ("失忆", "记忆"),
        ("又问一遍", "记忆"),
        ("重新要订单号", "记忆"),
        ("反复问", "记忆"),
    ]
    for key, cap in rules:
        if key in s:
            return cap
    return "不确定：对照四能力表再标"


def fill_table_rows() -> list[dict[str, str]]:
    """返回可写入笔记的对照表行。"""
    return list(AUDIT_05_07_INVENTORY_AGENT)
