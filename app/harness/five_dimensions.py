# app/harness/five_dimensions.py
"""课次 08.02 · 五维工程模型：资源 / 状态 / 信息流 / 安全 / 编排。

用法：
1. 对「当前 Agent 画像」打分（0–2）
2. 导出缺口表 → 映射到 08.0x / 已有模块落点
3. 长任务场景至少标出 3 个高风险缺口

分数直觉：
- 0 = 基本没有 / 靠运气
- 1 = 有一点，但不可运营
- 2 = 有明确机制，可指到代码或配置
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

DimId = Literal["resource", "state", "infoflow", "safety", "orchestration"]

DIMENSIONS: list[dict[str, str]] = [
    {
        "id": "resource",
        "name": "资源",
        "ask": "模型、Tool、文件、配额、超时谁管？",
        "collapse": "限流、账单爆炸、半截失败",
        "next_lesson": "统一 max_steps/超时进 Harness；Tool 目录受控",
        "maps_to": "M06 Loop max_steps；08.01 shell；后续配额中间件",
    },
    {
        "id": "state",
        "name": "状态",
        "ask": "任务进度、审批、thread 存在哪？",
        "collapse": "续跑丢、重复执行",
        "next_lesson": "case_id + Checkpointer；工单状态机",
        "maps_to": "07.05 Checkpointer；07.06/07.07 HITL + workflow State",
    },
    {
        "id": "infoflow",
        "name": "信息流",
        "ask": "上下文谁进谁出、何时压缩？",
        "collapse": "窗口爆、关键事实被挤掉",
        "next_lesson": "08.03 Context Engineering（按需 read）",
        "maps_to": "08.01 truncate 示意；08.03/08.06 压缩",
    },
    {
        "id": "safety",
        "name": "安全",
        "ask": "谁能调写入？输出如何护栏？",
        "collapse": "误操作、违规承诺",
        "next_lesson": "白名单 + 护栏 + HITL（先于炫技）",
        "maps_to": "06.06 safety；07.06 interrupt；08.01 shell",
    },
    {
        "id": "orchestration",
        "name": "编排",
        "ask": "Loop / 图 / 子 Agent 如何分工？",
        "collapse": "死循环、职责不清",
        "next_lesson": "07 图门禁；08.04/08.05 规划与子 Agent",
        "maps_to": "M06 Loop；M07 Graph；08.04 Deep Agents",
    },
]

# 检查顺序（课文建议）：安全 → 状态 → 信息流 → 资源 → 编排
CHECK_ORDER: list[DimId] = [
    "safety",
    "state",
    "infoflow",
    "resource",
    "orchestration",
]


@dataclass
class DimScore:
    """单维评分。"""

    dim_id: DimId
    name: str
    score: int  # 0–2
    as_is: str
    risk: str
    patch: str

    @property
    def is_gap(self) -> bool:
        return self.score <= 1


def _dim_meta(dim_id: str) -> dict[str, str]:
    for d in DIMENSIONS:
        if d["id"] == dim_id:
            return d
    raise KeyError(dim_id)


def score_profile(
    name: str,
    scores: dict[str, int],
    notes: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """对一个 Agent 画像按五维打分。

    scores: {dim_id: 0|1|2}
    notes: 可选覆盖 as_is / risk / patch
    """
    notes = notes or {}
    rows: list[DimScore] = []
    for d in DIMENSIONS:
        did = d["id"]  # type: ignore[assignment]
        sc = int(scores.get(did, 0))
        sc = max(0, min(2, sc))
        n = notes.get(did, {})
        rows.append(
            DimScore(
                dim_id=did,  # type: ignore[arg-type]
                name=d["name"],
                score=sc,
                as_is=n.get("as_is") or ("未评估" if sc == 0 else "部分具备"),
                risk=n.get("risk") or d["collapse"],
                patch=n.get("patch") or f"{d['next_lesson']}（→ {d['maps_to']}）",
            )
        )
    gaps = [r for r in rows if r.is_gap]
    return {
        "profile": name,
        "rows": rows,
        "gaps": gaps,
        "gap_count": len(gaps),
        "total_score": sum(r.score for r in rows),
        "max_score": 10,
    }


# ---------------------------------------------------------------------------
# 预制画像：FAQ（较省心）vs 长工单裸奔（五维易塌）vs 专栏现状（对照仓库）
# ---------------------------------------------------------------------------

FAQ_NOTES = {
    "resource": {
        "as_is": "短问答，偶发检索",
        "risk": "FAQ 压力小，但无统一超时仍可能挂起",
        "patch": "沿用默认超时即可；复杂了再上 Harness 配额",
    },
    "state": {
        "as_is": "无跨天任务",
        "risk": "多轮丢 sku 仍烦",
        "patch": "短记忆即可，不必强上 checkpoint",
    },
    "infoflow": {
        "as_is": "资料短",
        "risk": "FAQ 通常够",
        "patch": "08.03 按需加深",
    },
    "safety": {
        "as_is": "只读检索为主",
        "risk": "仍可能绝对承诺",
        "patch": "护栏保留（06.06/08.01）",
    },
    "orchestration": {
        "as_is": "单次检索链",
        "risk": "过度上图浪费",
        "patch": "保持单 Agent；分支多了再 07.04",
    },
}

LONG_TICKET_BARE_NOTES = {
    "resource": {
        "as_is": "无超时，Tool 随便调",
        "risk": "账单爆炸、半截失败",
        "patch": "资源维：max_steps/超时进 Harness",
    },
    "state": {
        "as_is": "只靠聊天记录",
        "risk": "续跑丢、重复赔付",
        "patch": "状态维：case_id + Checkpointer（07.05）",
    },
    "infoflow": {
        "as_is": "整包说明书进 Prompt",
        "risk": "窗口爆、关键轨迹被挤掉",
        "patch": "信息流维：08.03 按需 read",
    },
    "safety": {
        "as_is": "可直接「已赔付」话术",
        "risk": "违规承诺、误写入",
        "patch": "安全维：护栏 + HITL（先做）",
    },
    "orchestration": {
        "as_is": "单 Agent 一把梭",
        "risk": "死循环、职责不清",
        "patch": "编排维：07.07 工作流 + 08.04 规划",
    },
}

# 对照本仓库已落地能力（教学自评，可改）
COLUMN_AGENT_NOTES = {
    "resource": {
        "as_is": "有 max_steps / 重复检测（M06）；缺统一配额仪表",
        "risk": "多处重复配置",
        "patch": "收到 Harness 默认策略",
    },
    "state": {
        "as_is": "MemorySaver + thread_id + workflow State（M07）",
        "risk": "MemorySaver 不能上生产",
        "patch": "换 Redis/Postgres Checkpointer",
    },
    "infoflow": {
        "as_is": "仅有 truncate 示意（08.01）",
        "risk": "大网盘材料仍会爆窗",
        "patch": "08.03 Context Engineering",
    },
    "safety": {
        "as_is": "白名单/护栏/HITL 已有（06.06/07.06/08.01）",
        "risk": "未全链路接入每个入口",
        "patch": "统一走 harness.shell / middleware",
    },
    "orchestration": {
        "as_is": "Loop + Graph + 工作流角色（M06/M07）",
        "risk": "子 Agent 调度约定未成体系",
        "patch": "08.04/08.05 Deep Agents",
    },
}


def profile_faq() -> dict[str, Any]:
    """短 FAQ：多数维 1–2，演示「不必五维全拉满」。"""
    return score_profile(
        "FAQ 助手",
        {
            "resource": 1,
            "state": 1,
            "infoflow": 2,
            "safety": 1,
            "orchestration": 2,
        },
        FAQ_NOTES,
    )


def profile_long_ticket_bare() -> dict[str, Any]:
    """长工单裸奔：五维低分，≥3 缺口。"""
    return score_profile(
        "长工单助手（裸奔）",
        {
            "resource": 0,
            "state": 0,
            "infoflow": 0,
            "safety": 0,
            "orchestration": 0,
        },
        LONG_TICKET_BARE_NOTES,
    )


def profile_column_stack() -> dict[str, Any]:
    """专栏栈自评：部分维已有，信息流/生产状态仍是重点。"""
    return score_profile(
        "专栏 ai-service（当前）",
        {
            "resource": 1,
            "state": 1,
            "infoflow": 0,
            "safety": 2,
            "orchestration": 1,
        },
        COLUMN_AGENT_NOTES,
    )


def rows_as_table(result: dict[str, Any]) -> list[dict[str, str]]:
    """导出笔记表格行。"""
    out = []
    for r in result["rows"]:
        out.append(
            {
                "维度": r.name,
                "得分": f"{r.score}/2",
                "现状": r.as_is,
                "风险": r.risk,
                "计划补丁": r.patch,
            }
        )
    return out


def ordered_checkup(result: dict[str, Any]) -> list[dict[str, Any]]:
    """按建议检查顺序重排（安全优先）。"""
    by_id = {r.dim_id: r for r in result["rows"]}
    ordered = []
    for did in CHECK_ORDER:
        r = by_id[did]
        meta = _dim_meta(did)
        ordered.append(
            {
                "order": CHECK_ORDER.index(did) + 1,
                "name": r.name,
                "score": r.score,
                "ask": meta["ask"],
                "is_gap": r.is_gap,
                "patch": r.patch,
            }
        )
    return ordered


def why_long_task_harder() -> list[str]:
    """口述题：为何长任务比 FAQ 更吃五维。"""
    return [
        "多轮、跨小时、中间有人 → 状态维必须可恢复",
        "材料多 → 信息流必须按需加载，不能一次塞 Prompt",
        "可能换执行者 → 编排维要门禁与角色交接",
        "涉及赔付/承诺 → 安全维先于炫技",
        "Tool 多、时间长 → 资源维要步数/超时/配额",
    ]
