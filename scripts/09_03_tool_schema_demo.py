# scripts/09_03_tool_schema_demo.py
"""09.03 用 Schema 定义 Tool 演示。

【本课要感受的三件事】
1. list 能看到带「何时不用」+ 参数描述的 Schema
2. stdio call 成功（有 qty）+ 错误可回灌（error= 而非 Traceback）
3. 业务纯函数与 MCP 注册分层

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

from app.lessons.m09_03_tool_schema import lesson_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "tool_schema_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("Schema 清楚 = 模型敢调且调得对；MCP 只是可发现的壳")
    print("ROOT =", ROOT)

    suite = lesson_suite()
    note: list[str] = ["# 09.03 用 Schema 定义 Tool · 实跑记录\n", ""]

    # ---- STEP 1 · 坏 vs 好 ----
    print("\n" + "=" * 52, "STEP 1 · 坏 Schema vs 好 Schema")
    bg = suite["bad_vs_good"]
    print(f"  bad:  {bg['bad']}")
    print(f"  good: {bg['good']}")
    assert bg["good"]["name"] == "get_inventory"
    print("ASSERT: 能说出好坏差异 → PASS")
    note.append("## STEP 1 · 好坏对照\n")
    note.append(f"- bad: `{bg['bad']}`")
    note.append(f"- good: `{bg['good']}`\n")

    # ---- STEP 2 · 分层接线 ----
    print("\n" + "=" * 52, "STEP 2 · 普通函数 vs MCP 壳")
    w = suite["wiring"]
    print(f"  plain must_import={w['plain']['must_import']} → {w['plain']['result']}")
    print(f"  mcp   must_import={w['mcp']['must_import']} | {w['mcp']['shell']}")
    assert w["plain"]["must_import"] is True
    assert '"qty": 7' in w["plain"]["result"] or '"qty":7' in w["plain"]["result"].replace(" ", "")
    print("ASSERT: 纯函数可测；MCP 是壳 → PASS")
    note.append("## STEP 2 · 分层\n")
    note.append(f"- plain: `{w['plain']['result']}`")
    note.append(f"- {w['mcp']['shell']}\n")

    # ---- STEP 3 · list Schema ----
    print("\n" + "=" * 52, "STEP 3 · tools/list 检查 Schema")
    sc = suite["schemas"]
    print(f"  tools: {sc['tool_names']}")
    for row in sc["rows"]:
        print(
            f"  - {row['name']}: when_not={row['has_when_not']} "
            f"params_doc={row['params_documented']} required={row['required']}"
        )
        print(f"    desc: {row['description'][:80]}")
        print(f"    params: {row['param_descs']}")
    assert sc["has_get_inventory"]
    assert sc["all_have_when_not"]
    assert sc["all_params_documented"]
    print("ASSERT: description 含「不要」且参数有说明 → PASS")
    note.append("## STEP 3 · list Schema\n")
    note.append(f"- tools: `{sc['tool_names']}`")
    for row in sc["rows"]:
        note.append(f"- **{row['name']}**: {row['description'][:120]}")
        note.append(f"  - params: `{row['param_descs']}`")
    note.append("")

    # ---- STEP 4 · stdio 成功 call ----
    print("\n" + "=" * 52, "STEP 4 · stdio 成功 call")
    c = suite["calls"]
    print(f"  success: {c['success_text']}")
    print(f"  shipment: {c['shipment_text']}")
    print(f"  search: {c['search_preview'][:120]}")
    assert c["success_has_qty"]
    assert "get_inventory" in c["tool_names"]
    print("ASSERT: SHOE-RED-42 返回 qty → PASS")
    note.append("## STEP 4 · 成功 call\n")
    note.append(f"- input: sku=SHOE-RED-42")
    note.append(f"- output: `{c['success_text']}`")
    note.append(f"- shipment: `{c['shipment_text']}`\n")

    # ---- STEP 5 · 错误可回灌 ----
    print("\n" + "=" * 52, "STEP 5 · 错误可回灌（不崩）")
    print(f"  error: {c['error_text']}")
    assert c["error_is_soft"]
    assert c["no_traceback"]
    print("ASSERT: error=not_found 风格，无 Traceback → PASS")
    note.append("## STEP 5 · 错误 call\n")
    note.append(f"- input: sku=NO-SUCH-SKU")
    note.append(f"- output: `{c['error_text']}`\n")

    # ---- STEP 6 · 纯函数单测 ----
    print("\n" + "=" * 52, "STEP 6 · 业务层单测（不经 MCP）")
    u = suite["unit"]
    print(f"  ok_qty={u['ok_qty']} bad_soft={u['bad_soft']} ship_ok={u['ship_ok']}")
    assert u["ok_qty"] == 7 and u["bad_soft"] and u["ship_ok"]
    print("ASSERT: tools_inventory 可独立测 → PASS")
    note.append("## STEP 6 · unit\n")
    note.append(f"- `{u}`\n")

    assert suite.get("ok") is True
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: tool_schema 验收通过")


if __name__ == "__main__":
    main()
