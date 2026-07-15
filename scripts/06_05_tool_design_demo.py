# scripts/06_05_tool_design_demo.py
"""06.05 Tool 设计原则演示。

【本课要感受的三件事】
1. 坏 schema（manage / do_everything）评审低分；好 Tool（get_course）高分
2. 错误应回灌短字符串，而不是抛栈炸掉循环
3. 一事一工具 + Loop 组合，优于超级 Tool

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

from app.lessons.m06_05_tool_design import (  # noqa: E402
    CHECKLIST,
    demo_error_path_contrast,
    demo_granularity_contrast,
    demo_side_effect_warning,
    describe_schema,
    do_everything,
    get_course,
    improve_inventory_error_demo,
    manage,
    review_suite,
)
from app.tools.inventory import get_inventory  # noqa: E402

NOTE_PATH = ROOT / "notes" / "tool_design_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("本课以对照实验为主（不调 Chat）")
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 06.05 Tool 设计原则 · 实跑记录\n",
        "",
        "## 评审清单\n",
    ]
    for key, label in CHECKLIST:
        note.append(f"- `{key}`: {label}")
    note.append("")

    # ---- STEP 1 · 打印 schema ----
    print("\n" + "=" * 52, "STEP 1 · 打印 name / description / args")
    for t in (manage, do_everything, get_inventory, get_course):
        info = describe_schema(t)
        print(f"\n[{info['name']}]")
        print("  desc:", (info["description"] or "")[:120].replace("\n", " / "))
        props = (info.get("args_schema") or {}).get("properties") or {}
        print("  args:", list(props.keys()))
    print("ASSERT: 能列出坏/好 Tool 的 schema → PASS")
    note.append("## STEP 1 · Schema 摘要\n")
    for t in (manage, get_course):
        info = describe_schema(t)
        note.append(f"### {info['name']}\n")
        note.append(f"```\n{info['description'][:400]}\n```\n")

    # ---- STEP 2 · 评审打分 ----
    print("\n" + "=" * 52, "STEP 2 · 评审清单打分")
    results = review_suite()
    for r in results:
        print(f"  {r.as_row()}  notes={r.notes[:1] or '-'}")
    by_name = {r.tool_name: r for r in results}
    assert by_name["manage"].passed <= 3
    assert by_name["do_everything"].passed <= 3
    assert by_name["get_course"].passed >= 6
    assert by_name["get_inventory"].passed >= 5
    print("ASSERT: 坏 Tool 低分 / get_course 高分 → PASS")
    note.append("## STEP 2 · 打分\n")
    note.append("| Tool | 得分 | 备注 |")
    note.append("|------|------|------|")
    for r in results:
        note.append(
            f"| {r.tool_name} | {r.passed}/{r.total} | {'; '.join(r.notes) or '—'} |"
        )
    note.append("")

    # ---- STEP 3 · 错误路径 ----
    print("\n" + "=" * 52, "STEP 3 · 错误：抛栈 vs 可读字符串")
    err = demo_error_path_contrast()
    print("bad_manage:", err["bad_manage"])
    print("good_not_found:", err["good_not_found"])
    print("good_empty:", err["good_empty"])
    assert err["bad_manage"]["ok"] is False and err["bad_manage"]["raised"]
    assert err["good_not_found"]["ok"] is True
    assert "error=not_found" in err["good_not_found"]["observation"]
    assert "hint=" in err["good_not_found"]["observation"]
    assert "error=empty" in err["good_empty"]["observation"]
    print("ASSERT: 好 Tool 失败仍返回字符串且含 hint → PASS")
    note.append("## STEP 3 · 错误回灌\n")
    note.append(f"- 坏 manage: `{err['bad_manage']}`")
    note.append(f"- 好 get_course: `{err['good_not_found']['observation']}`\n")

    # ---- STEP 4 · 粒度 ----
    print("\n" + "=" * 52, "STEP 4 · 超级 Tool vs 一事一工具")
    gran = demo_granularity_contrast()
    print("goal:", gran["user_goal"])
    print("mega:", [c.get("observation") or c.get("raised") for c in gran["mega_calls"]])
    print("fine:", [c["observation"] for c in gran["fine_calls"]])
    assert all(c["ok"] for c in gran["fine_calls"])
    assert "stock=12" in gran["fine_calls"][0]["observation"]
    assert "CS101" in gran["fine_calls"][1]["observation"]
    print("ASSERT: 细粒度两 Tool 可组合完成目标 → PASS")
    note.append("## STEP 4 · 粒度\n")
    note.append(f"- 目标: {gran['user_goal']}")
    note.append(f"- 细粒度: `{gran['fine_calls']}`")
    note.append(f"- 教训: {gran['lesson']}\n")

    # ---- STEP 5 · 副作用警告 ----
    print("\n" + "=" * 52, "STEP 5 · 写入副作用不该混进只读超级 Tool")
    side = demo_side_effect_warning()
    print(side["bad_refund_observation"])
    assert "refund" in str(side["bad_refund_observation"]).lower() or side[
        "bad_refund_observation"
    ]["ok"]
    print("ASSERT: 反例可演示（见笔记，正道留给 06.06 HITL）→ PASS")
    note.append("## STEP 5 · 副作用\n")
    note.append(f"- `{side['bad_refund_observation']}`")
    note.append(f"- {side['lesson']}\n")

    # ---- STEP 6 · 错误串改进示意 + 好 Tool 成功路径 ----
    print("\n" + "=" * 52, "STEP 6 · 改进错误串示意 + get_course 成功")
    imp = improve_inventory_error_demo("EARPHONE")
    print("before:", imp["before"])
    print("after :", imp["after_recommended"])
    ok_course = get_course.invoke({"course_id": "CS101"})
    print("get_course OK:", ok_course)
    assert imp["before"] == "not_found"
    assert "hint=" in imp["after_recommended"]
    assert "schedule=" in ok_course
    print("ASSERT: 推荐 error=/hint= 格式 + 新 Tool 成功路径 → PASS")
    note.append("## STEP 6 · 改好记录\n")
    note.append("- 新增好 Tool: `app/tools/course_schedule.py` → `get_course`")
    note.append(f"- 库存错误串对照 before=`{imp['before']}` / after=`{imp['after_recommended']}`")
    note.append(f"- 成功样例: `{ok_course}`")
    note.append(f"- 说明: {imp['note']}\n")

    note.append("## 结论\n")
    note.append("- Tool 是 Agent 的手：描述清晰、一事一工具、失败可回灌。")
    note.append("- 超级 Tool 与硬抛异常是常见翻车源。")
    note.append("- 有副作用操作单独拆出并上 HITL（06.06）。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: tool_design 验收通过")


if __name__ == "__main__":
    main()
