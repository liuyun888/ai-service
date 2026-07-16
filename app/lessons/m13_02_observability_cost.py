# app/lessons/m13_02_observability_cost.py
"""课次 13.02 · 可观测 + 金标评估 + 成本笔记一键产出。

产出物：
- tmp/trace-final.json（可回放 Trace）
- notes/cost_tuning_note.md（成本与调优笔记）
- 金标通过率 + 专栏自检表
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.harness.middleware.chain import run_middleware_pipeline
from app.harness.middleware.trace import export_trace
from app.lessons.m08_06_middleware_eval import (
    DEMO_DRAFT,
    DEMO_TOOL_OBS,
    DEMO_USER,
    run_compaction_demo,
)
from app.ops.column_checklist import column_self_check
from app.ops.cost import estimate_request_cost_cny, iteration_mantra, list_cost_levers
from app.ops.eval_gold import run_gold_checks

ROOT = Path(__file__).resolve().parents[2]


def export_final_trace(*, out_path: Path | None = None) -> Path:
    """跑一轮中间件链路，导出最终 Trace（正文点名的 tmp/trace-final.json）。"""
    path = out_path or (ROOT / "tmp" / "trace-final.json")
    ctx = run_middleware_pipeline(
        DEMO_USER,
        draft_reply=DEMO_DRAFT,
        tool_name="search_knowledge",
        tool_observation=DEMO_TOOL_OBS,
        prompt_for_log=f"system…\nuser:{DEMO_USER}",
    )
    compact = run_compaction_demo()
    return export_trace(
        ctx,
        path,
        extra={
            "lesson": "13.02",
            "scenario": "commitment_guard_final",
            "request_id_hint": "与 BFF X-Request-Id 对齐时写入同一字段",
            "compaction": {
                "before_chars": compact["before_chars"],
                "after_chars": compact["after_chars"],
                "saved_chars": compact.get("saved_chars"),
            },
            "langsmith_note": "有平台时把同一 trace_id 挂到 LangSmith；无平台用本 JSON 即可",
        },
    )


def write_cost_tuning_note(
    *,
    note_path: Path | None = None,
    gold: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
    checklist: dict[str, Any] | None = None,
    waste_point: str = "max_steps 过大 / 重复检索（示例）",
) -> Path:
    """按正文模板写成本与调优笔记。"""
    path = note_path or (ROOT / "notes" / "cost_tuning_note.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    gold = gold or {}
    cost = cost or {}
    checklist = checklist or {}
    levers = list_cost_levers()
    mantra = iteration_mantra()
    lines = [
        "# 成本与调优笔记",
        "",
        "## 当前",
        f"- 模型：演示粗估（非厂商账单）；本轮 total_tokens≈`{cost.get('total_tokens')}`",
        f"- 估成本/请求：`{cost.get('est_cost_cny')}` 元（{cost.get('price_note')}）",
        "- 月估：用「日请求量 × 单次成本」自己乘，勿照抄演示单价",
        "",
        "## 瓶颈（来自 Trace）",
        f"- Top1 浪费点：{waste_point}",
        "- 本示例 Trace 还展示：护栏拦截绝对承诺、PII 脱敏、TokenLog",
        "",
        "## 本周改动（Harness，非换模）",
        "1. 降低 max_steps / 加重复检索检测",
        "2. 热门 FAQ 走缓存，不调模型",
        "3. Compaction：长对话先压缩再生成",
        "",
        "## 金标",
        f"- 改前/改后通过率（本课基线）：`{gold.get('passed')}/{gold.get('total')}`"
        f" = `{gold.get('pass_rate')}`",
        "- 扩到 20 条后再谈换大模型",
        "",
        "## 成本杠杆优先序",
    ]
    for row in levers:
        lines.append(f"- {row['order']}. **{row['lever']}**：{row['why']}")
    lines.extend(
        [
            "",
            "## 迭代口诀",
            *[f"- {m}" for m in mantra],
            "",
            "## 专栏自检",
            f"- 已具备：`{checklist.get('ready_count')}/{checklist.get('total')}`",
        ]
    )
    for r in checklist.get("ready") or []:
        lines.append(f"  - [x] {r['id']} {r['item']}")
    for r in checklist.get("pending") or []:
        lines.append(f"  - [ ] {r['id']} {r['item']}（待补：`{r['path']}`）")
    lines.extend(["", "SUMMARY: 13.02 成本笔记已生成", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path.resolve()


def demo_suite() -> dict[str, Any]:
    """一键：Trace + 金标 + 成本 + 自检 + 笔记。"""
    trace_path = export_final_trace()
    gold = run_gold_checks()
    cost = estimate_request_cost_cny(
        prompt=f"system…\nuser:{DEMO_USER}",
        completion=DEMO_DRAFT,
    )
    checklist = column_self_check(ROOT)
    note_path = write_cost_tuning_note(gold=gold, cost=cost, checklist=checklist)
    # Trace 文件可读
    doc = json.loads(trace_path.read_text(encoding="utf-8"))
    ok = (
        gold["ok"]
        and checklist["ok"]
        and trace_path.is_file()
        and note_path.is_file()
        and bool(doc.get("trace_id"))
        and bool(doc.get("events"))
    )
    return {
        "ok": ok,
        "trace_path": str(trace_path),
        "note_path": str(note_path),
        "gold": {"passed": gold["passed"], "total": gold["total"], "pass_rate": gold["pass_rate"]},
        "cost": cost,
        "checklist": {
            "ready_count": checklist["ready_count"],
            "total": checklist["total"],
        },
        "mantra": iteration_mantra(),
        "trace_id": doc.get("trace_id"),
    }
