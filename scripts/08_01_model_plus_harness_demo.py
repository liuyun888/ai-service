# scripts/08_01_model_plus_harness_demo.py
"""08.01 Agent = Model + Harness 演示。

【本课要感受的三件事】
1. 三层：Model / Framework / Harness 不混谈
2. 同一问句：裸奔 vs Harness（鉴权/护栏/Trace）可运营性不同
3. 目录骨架 + 缺口表：知道该往 Harness 上移什么

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

from app.harness.shell import gap_audit_template, layer_map  # noqa: E402
from app.lessons.m08_01_model_plus_harness import (  # noqa: E402
    check_harness_skeleton,
    demo_contrast,
)

NOTE_PATH = ROOT / "notes" / "model_plus_harness_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("公式: Agent ≈ Model + Harness")
    print("ROOT =", ROOT)

    note: list[str] = [
        "# 08.01 Agent = Model + Harness · 实跑记录\n",
        "",
        "## 公式\n",
        "`Agent ≈ Model + Harness`；Framework 管编排，Harness 管运营外壳。\n",
        "",
    ]

    # ---- STEP 1 · 目录骨架 ----
    print("\n" + "=" * 52, "STEP 1 · Harness 目录骨架")
    sk = check_harness_skeleton()
    for row in sk["rows"]:
        print(f"  [{'OK' if row['exists'] else 'MISS'}] {row['path']}")
    assert sk["ok"], sk
    print("ASSERT: middleware/context/memory/skills 齐全 → PASS")
    note.append("## STEP 1 · 目录\n")
    for row in sk["rows"]:
        note.append(f"- `{row['path']}` exists={row['exists']}")
    note.append("")

    # ---- STEP 2 · 三层表 ----
    print("\n" + "=" * 52, "STEP 2 · 三层职责")
    layers = layer_map()
    for L in layers:
        print(f"  [{L['layer']}] {L['duty']}")
        print(f"         例: {L['example']} | 不该: {L['not']}")
    assert {x["layer"] for x in layers} == {"Model", "Framework", "Harness"}
    print("ASSERT: 三层可区分 → PASS")
    note.append("## STEP 2 · 三层\n")
    note.append("| 层 | 职责 | 例子 | 不该管 |")
    note.append("|----|------|------|--------|")
    for L in layers:
        note.append(
            f"| {L['layer']} | {L['duty']} | {L['example']} | {L['not']} |"
        )
    note.append("")

    # ---- STEP 3 · 对照：裸奔 vs Harness ----
    print("\n" + "=" * 52, "STEP 3 · 同一问句两套外壳")
    pair = demo_contrast()
    bare, harness = pair["bare"], pair["harness"]
    print("Q: 退货要几天？")
    print("bare reply:", (bare.get("reply") or "")[:100])
    print("bare trace len:", len(bare.get("trace") or []))
    print("harness reply:", (harness.get("reply") or "")[:100])
    print("harness trace:")
    for ev in harness.get("trace") or []:
        print(f"  - {ev['name']}: {ev['detail'][:80]}")
    assert bare["mode"] == "bare" and not bare["trace"]
    assert harness["mode"] == "harness" and len(harness["trace"]) >= 3
    assert harness.get("tenant_ok") is True
    assert "7" in (bare.get("reply") or "") or "退货" in (bare.get("reply") or "")
    print("ASSERT: 裸奔无 Trace；Harness 有多步 Trace → PASS")
    note.append("## STEP 3 · 对照\n")
    note.append(f"- bare: {bare.get('reply')}")
    note.append(f"- harness: {harness.get('reply')}")
    note.append(f"- harness trace: `{harness.get('trace')}`\n")

    # ---- STEP 4 · 租户拒绝 + 承诺护栏 ----
    print("\n" + "=" * 52, "STEP 4 · Harness 挡租户 / 挡承诺")
    bad = pair["harness_bad_tenant"]
    prom = pair["harness_promise_blocked"]
    print("bad tenant reply:", bad.get("reply"))
    print("promise guard_ok:", prom.get("guard_ok"), "|", (prom.get("reply") or "")[:80])
    assert bad.get("tenant_ok") is False
    assert "无权" in (bad.get("reply") or "") or "租户" in (bad.get("reply") or "")
    assert prom.get("guard_ok") is False
    assert "保证明天" not in (prom.get("reply") or "")
    print("ASSERT: 非法租户与绝对承诺被外壳拦住 → PASS")
    note.append("## STEP 4 · 拦截\n")
    note.append(f"- bad tenant: {bad.get('reply')}")
    note.append(f"- promise blocked: {prom.get('reply')}\n")

    # ---- STEP 5 · 缺口表 ----
    print("\n" + "=" * 52, "STEP 5 · 现有 Agent 缺口表")
    gaps = gap_audit_template()
    print(f"{'能力':<16} | {'现在在哪':<40} | 上移?")
    print("-" * 80)
    for g in gaps:
        print(f"{g['capability']:<16} | {g['now_layer'][:40]:<40} | {g['move_to_harness'][:24]}")
    assert any(g["capability"] == "max_steps" for g in gaps)
    assert any("Harness" in g["move_to_harness"] or "已在" in g["move_to_harness"] for g in gaps)
    print("ASSERT: 缺口表填满 → PASS")
    note.append("## STEP 5 · 缺口表\n")
    note.append("| 能力 | 现在在哪一层？ | 是否应上移到 Harness？ |")
    note.append("|------|----------------|------------------------|")
    for g in gaps:
        note.append(
            f"| {g['capability']} | {g['now_layer']} | {g['move_to_harness']} |"
        )
    note.append("")

    note.append("## 结论\n")
    note.append("- 模型可换，Harness 要稳；图/Loop 跑在外壳里，外壳不替代图。")
    note.append("- Demo→生产：同一答案，可运营性靠 Harness。")
    note.append("- 下一课：五维工程模型系统扫缺口。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: model_plus_harness 验收通过")


if __name__ == "__main__":
    main()
