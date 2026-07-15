# scripts/06_02_four_capabilities_demo.py
"""06.02 Agent 四能力演示。

【本课要感受的三件事】
1. 四能力是检查清单，不是四个玄学形容词
2. 「缺反思」可以跑出死磕；「有反思」会停
3. 记忆/规划也能用最小代码演示，再对照填表

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m06_02_four_capabilities import (  # noqa: E402
    classify_fault,
    demo_memory_two_turns,
    demo_missing_reflection,
    demo_planning_two_steps,
    demo_with_reflection,
    fill_table_rows,
)

NOTE_PATH = ROOT / "notes" / "agent_four_capabilities_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("本课以对照实验为主（默认不调 Chat）")
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 06.02 Agent 四能力 · 实跑记录\n",
        "",
        "## 公式复习\n",
        "`Agent ≈ Model + Tools + 控制策略`；四能力用来检查「装得全不全」。\n",
        "",
    ]

    # ---- STEP 1 · 针对 05.07 填对照表 ----
    print("\n" + "=" * 52, "STEP 1 · 05.07 库存 Agent 四能力审计表")
    rows = fill_table_rows()
    print(
        f"{'能力':<6} | {'当前实现':<28} | {'缺口'}"
    )
    print("-" * 72)
    for r in rows:
        print(f"{r['能力']:<6} | {r['当前实现'][:28]:<28} | {r['缺口'][:28]}")
        assert r.get("缺口"), "每行应有缺口（至少写「暂无」）"
    print("ASSERT: 对照表四行填满且含缺口 → PASS")
    note.append("## STEP 1 · 对照表\n")
    note.append("| 能力 | 我的场景表现 | 当前实现 | 缺口 |")
    note.append("|------|--------------|----------|------|")
    for r in rows:
        note.append(
            f"| {r['能力']} | {r['我的场景表现']} | {r['当前实现']} | {r['缺口']} |"
        )
    note.append("")

    # ---- STEP 2 · 缺反思 vs 有反思 ----
    print("\n" + "=" * 52, "STEP 2 · 缺反思（死磕）vs 有反思（停下）")
    bad = demo_missing_reflection(times=5)
    print("缺反思:", bad["fault"])
    print("observations:", bad["observations"][:3], "...")
    assert bad["all_not_found"] and len(bad["observations"]) == 5
    good = demo_with_reflection()
    print("有反思 decision:", good["decision"])
    print("answer:", good["answer"])
    assert good["extra_calls"] == 0 and good["decision"] == "stop_and_ask_user"
    print("ASSERT: 同一 not_found，缺反思连打 / 有反思停 → PASS")
    note.append("## STEP 2 · 反思对照\n")
    note.append(f"- 缺反思: `{bad['fault']}`")
    note.append(f"- 有反思: `{good['answer']}`\n")

    # ---- STEP 3 · 记忆两轮 ----
    print("\n" + "=" * 52, "STEP 3 · 记忆：第二轮不再丢 sku")
    mem = demo_memory_two_turns()
    print("turn1:", mem["turn1"])
    print("turn2:", mem["turn2"])
    print("无记忆:", mem["without_memory_answer"])
    print("有记忆:", mem["with_memory_answer"])
    assert "stock=12" in mem["with_memory_answer"]
    assert "无法查询" in mem["without_memory_answer"]
    print("ASSERT: 短记忆补全 sku → PASS")
    note.append("## STEP 3 · 记忆\n")
    note.append(f"- 无记忆: {mem['without_memory_answer']}")
    note.append(f"- 有记忆: {mem['with_memory_answer']}\n")

    # ---- STEP 4 · 规划两步 ----
    print("\n" + "=" * 52, "STEP 4 · 规划：库存 + 运单两步")
    plan = demo_planning_two_steps()
    for p in plan["plan"]:
        print(" ", p)
    for s in plan["steps_done"]:
        print(f"  done {s['step']}: {s['observation']}")
    print(plan["summary"])
    assert len(plan["steps_done"]) == 2
    print("ASSERT: 按计划顺序调两个 Tool → PASS")
    note.append("## STEP 4 · 规划\n")
    for p in plan["plan"]:
        note.append(f"- {p}")
    note.append(f"- 汇总: {plan['summary']}\n")

    # ---- STEP 5 · 故障归类练习 ----
    print("\n" + "=" * 52, "STEP 5 · 故障话术归到「缺哪项」")
    samples = [
        "模型越查 not_found 越调同一 sku",
        "客服每轮都重新要订单号",
        "只会聊天说「大概有货」从不调工具",
        "该先查单再查物流，结果直接编物流",
    ]
    for s in samples:
        cap = classify_fault(s)
        print(f"  [{cap}] {s}")
        assert cap != "不确定：对照四能力表再标" or "编物流" in s
    # 第四条应归规划
    assert classify_fault(samples[3]) == "规划"
    assert classify_fault(samples[0]) == "反思"
    assert classify_fault(samples[1]) == "记忆"
    assert classify_fault(samples[2]) == "工具"
    print("ASSERT: 故障可归到四能力 → PASS")
    note.append("## STEP 5 · 故障归类\n")
    for s in samples:
        note.append(f"- `{classify_fault(s)}` ← {s}")
    note.append("")

    note.append("## 结论\n")
    note.append("- 四能力是设计检查清单：缺哪项，故障长哪样。")
    note.append("- 反思要用 Observation 驱动分支，不是写鸡汤。")
    note.append("- 简单任务可裁剪；复杂办结再加规划/记忆/图与 Harness。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: four_capabilities 验收通过")


if __name__ == "__main__":
    main()
