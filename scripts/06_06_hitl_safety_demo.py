# scripts/06_06_hitl_safety_demo.py
"""06.06 人机协作与安全边界演示。

【本课要感受的三件事】
1. 工具白名单：refund 等写入动作调不着
2. 输出护栏：绝对承诺句发不出去（代码强制，不靠 System）
3. HITL / 转人工：退款与连续失败会暂停，并带摘要

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

from app.harness.middleware.safety import (  # noqa: E402
    BLOCK_PATTERNS,
    TOOL_WHITELIST,
    check_tool_allowed,
)
from app.lessons.m06_06_hitl_safety import run_acceptance_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "hitl_safety_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("白名单 Tool:", sorted(TOOL_WHITELIST))
    print("护栏样例:", BLOCK_PATTERNS[:3], "...")
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 06.06 人机协作与安全边界 · 实跑记录\n",
        "",
        f"- TOOL_WHITELIST: `{sorted(TOOL_WHITELIST)}`",
        f"- BLOCK_PATTERNS: `{list(BLOCK_PATTERNS)}`",
        "",
    ]

    suite = run_acceptance_suite()

    # ---- STEP 1 · 白名单 ----
    print("\n" + "=" * 52, "STEP 1 · 工具白名单（只读放行 / 写入拒绝）")
    ok, reason_ok = check_tool_allowed("get_inventory")
    bad, reason_bad = check_tool_allowed("refund")
    print("get_inventory:", ok, reason_ok)
    print("refund:", bad, reason_bad)
    assert ok is True
    assert bad is False and "hitl_required" in reason_bad
    unknown, reason_u = check_tool_allowed("send_email_blast")
    assert unknown is False and "not_in_whitelist" in reason_u
    print("ASSERT: 白名单拦截写入/未知 Tool → PASS")
    note.append("## STEP 1 · 白名单\n")
    note.append(f"- get_inventory → `{reason_ok}`")
    note.append(f"- refund → `{reason_bad}`")
    note.append(f"- send_email_blast → `{reason_u}`\n")

    # ---- STEP 2 · 正常库存放行 ----
    print("\n" + "=" * 52, "STEP 2 · 正常查库存 → 放行")
    normal = suite["normal"]
    print("user:", normal["user"])
    print("obs:", normal["tool_call"]["observation"])
    print("export:", normal["export"]["kind"], normal["export"]["reply"][:120])
    assert normal["tool_call"]["executed"] is True
    assert normal["export"]["escalated"] is False
    assert normal["export"]["guard_ok"] is True
    assert "stock=12" in normal["export"]["reply"]
    print("ASSERT: 只读查询完整放行 → PASS")
    note.append("## STEP 2 · 正常放行\n")
    note.append(f"- reply: {normal['export']['reply']}\n")

    # ---- STEP 3 · 输出护栏 ----
    print("\n" + "=" * 52, "STEP 3 · 绝对承诺 → 护栏改写")
    promise = suite["promise"]
    print("draft:", promise["draft"])
    print("reply:", promise["export"]["reply"][:160])
    print("hit:", promise["export"].get("hit_pattern") or promise["bare_guard"].hit_pattern)
    assert promise["export"]["guard_ok"] is False or promise["bare_guard"].ok is False
    assert "保证明天" not in promise["export"]["reply"]
    assert "绝对能到" not in promise["export"]["reply"]
    assert "不能做出该类绝对承诺" in promise["export"]["reply"]
    diag = suite["diagnose"]
    assert "一定治愈" not in diag["export"]["reply"]
    print("ASSERT: 风险句被拦，安全模板发出 → PASS")
    note.append("## STEP 3 · 输出护栏\n")
    note.append(f"- draft: `{promise['draft']}`")
    note.append(f"- reply: {promise['export']['reply']}")
    note.append(f"- diagnose reply: {diag['export']['reply']}\n")

    # ---- STEP 4 · 退款 HITL ----
    print("\n" + "=" * 52, "STEP 4 · 直接退款 → HITL（不自动执行）")
    refund = suite["refund"]
    print("whitelist_block:", refund["whitelist_block"]["observation"][:120])
    print("kind:", refund["export"]["kind"])
    print("reply:", refund["export"]["reply"][:200])
    assert refund["whitelist_block"]["executed"] is False
    assert refund["export"]["escalated"] is True
    assert refund["export"]["hitl"] is True
    assert "待人工确认" in refund["export"]["reply"]
    assert "转人工摘要" in refund["export"]["reply"]
    print("ASSERT: 退款走 HITL + 摘要，未执行退款 Tool → PASS")
    note.append("## STEP 4 · 退款 HITL\n")
    note.append(f"- block: `{refund['whitelist_block']['observation']}`")
    note.append(f"- reply:\n\n{refund['export']['reply']}\n")

    # ---- STEP 5 · 连续失败转人工 ----
    print("\n" + "=" * 52, "STEP 5 · 连续 Tool 失败 → 转人工")
    fails = suite["tool_fails"]
    print("tool_fails:", fails["tool_fails"])
    print("kind:", fails["export"]["kind"], "|", fails["export"]["reason"])
    print("reply:", fails["export"]["reply"][:200])
    assert fails["tool_fails"] >= 2
    assert fails["export"]["escalated"] is True
    assert "转人工摘要" in fails["export"]["reply"]
    assert "NO-SUCH-SKU" in fails["export"]["handoff_summary"]
    print("ASSERT: 失败阈值触发转人工且摘要含轨迹 → PASS")
    note.append("## STEP 5 · 连续失败\n")
    note.append(f"- reason: {fails['export']['reason']}")
    note.append(f"- summary:\n\n{fails['export']['handoff_summary']}\n")

    # ---- STEP 6 · 用户要人工 ----
    print("\n" + "=" * 52, "STEP 6 · 用户明确转人工")
    human = suite["ask_human"]
    print("reply:", human["export"]["reply"][:160])
    assert human["export"]["escalated"] is True
    assert human["export"]["kind"] == "human"
    print("ASSERT: 关键词转人工 → PASS")
    note.append("## STEP 6 · 要人工\n")
    note.append(f"- kind: {human['export']['kind']}")
    note.append(f"- reply: {human['export']['reply']}\n")

    note.append("## 结论\n")
    note.append("- 安全边界要代码强制：白名单 + 出口护栏 + HITL/转人工。")
    note.append("- 转人工必须带摘要，避免用户重讲。")
    note.append("- 保留只读 Tool；写入默认禁止或等人确认（M07 图上 pause 更自然）。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: hitl_safety 验收通过")


if __name__ == "__main__":
    main()
