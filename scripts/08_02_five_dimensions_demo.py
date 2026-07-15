# scripts/08_02_five_dimensions_demo.py
"""08.02 五维工程模型演示。

【本课要感受的三件事】
1. 五维名称与一句话定义能对照打分
2. 长工单裸奔 ≥3 个缺口，且映射到后续课
3. 检查顺序：安全优先，不是先炫编排

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m08_02_five_dimensions import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "five_dimensions_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("五维 = 资源 / 状态 / 信息流 / 安全 / 编排")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = [
        "# 08.02 五维工程模型 · 实跑记录\n",
        "",
        "## 五维定义\n",
    ]
    for d in suite["dimensions"]:
        note.append(f"- **{d['name']}**：{d['ask']} → 塌了：{d['collapse']}")
    note.append("")

    # ---- STEP 1 · 五维名 ----
    print("\n" + "=" * 52, "STEP 1 · 五维名称与一句话")
    names = []
    for d in suite["dimensions"]:
        print(f"  [{d['name']}] {d['ask']}")
        names.append(d["name"])
    assert names == ["资源", "状态", "信息流", "安全", "编排"]
    print("ASSERT: 五维名称齐全 → PASS")

    # ---- STEP 2 · 长工单缺口表 ----
    print("\n" + "=" * 52, "STEP 2 · 长工单裸奔缺口表")
    long_bare = suite["long_bare"]
    print(
        f"profile={long_bare['profile']} score={long_bare['total_score']}/{long_bare['max_score']} gaps={long_bare['gap_count']}"
    )
    print(f"{'维度':<6} | 得分 | 现状")
    print("-" * 56)
    for row in suite["long_gaps"]:
        print(f"{row['维度']:<6} | {row['得分']:<4} | {row['现状'][:36]}")
    assert long_bare["gap_count"] >= 3
    assert long_bare["total_score"] <= 3
    print("ASSERT: 长工单 ≥3 缺口 → PASS")
    note.append("## STEP 2 · 长工单裸奔\n")
    note.append("| 维度 | 得分 | 现状 | 风险 | 计划补丁 |")
    note.append("|------|------|------|------|----------|")
    for row in suite["long_gaps"]:
        note.append(
            f"| {row['维度']} | {row['得分']} | {row['现状']} | {row['风险']} | {row['计划补丁']} |"
        )
    note.append("")

    # ---- STEP 3 · 补丁映射 08.0x ----
    print("\n" + "=" * 52, "STEP 3 · 缺口 → 后续课映射")
    mapped = 0
    for row in suite["long_gaps"]:
        if "08." in row["计划补丁"] or "07." in row["计划补丁"] or "06." in row["计划补丁"]:
            mapped += 1
            print(f"  {row['维度']}: {row['计划补丁'][:60]}")
    assert mapped >= 3
    print("ASSERT: 至少 3 项可映射到模块内补丁 → PASS")
    note.append("## STEP 3 · 映射\n")
    note.append(f"- 可映射补丁行数: {mapped}\n")

    # ---- STEP 4 · 检查顺序 ----
    print("\n" + "=" * 52, "STEP 4 · 建议检查顺序（安全优先）")
    order = suite["checkup_order"]
    for item in order:
        flag = "GAP" if item["is_gap"] else "ok"
        print(f"  {item['order']}. {item['name']} [{flag}] score={item['score']}")
    assert order[0]["name"] == "安全"
    print("ASSERT: 第一优先是安全 → PASS")
    note.append("## STEP 4 · 检查顺序\n")
    for item in order:
        note.append(
            f"{item['order']}. {item['name']} score={item['score']} gap={item['is_gap']}"
        )
    note.append("")

    # ---- STEP 5 · FAQ vs 长任务 ----
    print("\n" + "=" * 52, "STEP 5 · FAQ vs 长任务为何更吃五维")
    faq = suite["faq"]
    print(f"FAQ score={faq['total_score']}/10 gaps={faq['gap_count']}")
    print(f"长工单 score={long_bare['total_score']}/10 gaps={long_bare['gap_count']}")
    for line in suite["why_long"]:
        print(" -", line)
    assert faq["total_score"] > long_bare["total_score"]
    assert faq["gap_count"] < long_bare["gap_count"]
    print("ASSERT: 长任务缺口显著多于 FAQ → PASS")
    note.append("## STEP 5 · 为何长任务更吃五维\n")
    note.append(f"- FAQ: {faq['total_score']}/10；长工单: {long_bare['total_score']}/10")
    for line in suite["why_long"]:
        note.append(f"- {line}")
    note.append("")

    # ---- STEP 6 · 专栏栈自评 ----
    print("\n" + "=" * 52, "STEP 6 · 专栏 ai-service 自评（可改）")
    col = suite["column"]
    print(f"score={col['total_score']}/10 gaps={col['gap_count']}")
    for r in col["rows"]:
        print(f"  {r.name}: {r.score}/2 | {r.as_is[:40]}")
    # 信息流应是明确缺口（截断仅示意）
    info = next(r for r in col["rows"] if r.name == "信息流")
    assert info.score <= 1
    assert col["gap_count"] >= 1
    print("ASSERT: 专栏栈仍有可补维（至少信息流）→ PASS")
    note.append("## STEP 6 · 专栏自评\n")
    note.append("| 维度 | 得分 | 现状 | 计划补丁 |")
    note.append("|------|------|------|----------|")
    for r in col["rows"]:
        note.append(f"| {r.name} | {r.score}/2 | {r.as_is} | {r.patch} |")
    note.append("")

    note.append("## 结论\n")
    note.append("- 翻车先定位哪一维塌了，再对症下药，而不是只加 Prompt。")
    note.append("- 长任务五维全亮；FAQ 可裁剪。")
    note.append("- 下一课：信息流 —— Context Engineering。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: five_dimensions 验收通过")


if __name__ == "__main__":
    main()
