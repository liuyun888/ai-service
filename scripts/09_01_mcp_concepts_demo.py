# scripts/09_01_mcp_concepts_demo.py
"""09.01 MCP 概念演示。

【本课要感受的三件事】
1. 四要素：Server / Client / Tool / Resource 能分开说
2. 普通函数 Tool vs MCP 形发现+调用：差异在接线，不在业务
3. Tool≠Resource；记下本模块第一个 Tool=search_docs

工作目录：必须在 ai-service/ 下。
本课不装官方 mcp 包也能跑；真 stdio Server 见 09.02。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m09_01_mcp_concepts import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "mcp_concepts_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("MCP ≈ AI 工具的 USB；本课=进程内迷你协议讲概念")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = [
        "# 09.01 MCP 概念 · 实跑记录\n",
        "",
        "## 拓扑\n",
        "```",
        suite["topology"].rstrip(),
        "```",
        "",
    ]

    # ---- STEP 1 · 四要素 ----
    print("\n" + "=" * 52, "STEP 1 · 四要素一句话")
    names = []
    for row in suite["elements"]:
        print(f"  [{row['name']}] {row['one_liner']} ← {row['ask']}")
        names.append(row["name"])
        note.append(f"- **{row['name']}**：{row['one_liner']}")
    assert names == ["Server", "Client", "Tool", "Resource"]
    print("ASSERT: 四要素齐全且顺序固定 → PASS")
    note.append("")

    # ---- STEP 2 · 拓扑 ----
    print("\n" + "=" * 52, "STEP 2 · Client–Server–Tool 关系")
    print(suite["topology"])
    assert "search_docs" in suite["topology"]
    assert "policy://return" in suite["topology"]
    print("ASSERT: 图中同时有 Tool 与 Resource → PASS")

    # ---- STEP 3 · 普通 vs MCP ----
    print("\n" + "=" * 52, "STEP 3 · 普通函数 Tool vs MCP 形")
    c = suite["contrast"]
    print(f"  query: {c['query']}")
    print(f"  plain must_import={c['plain']['must_import_function']}")
    print(f"  plain result: {str(c['plain']['result'])[:120]}")
    print(f"  mcp  must_import={c['mcp']['must_import_function']}")
    print(f"  mcp  tools={c['mcp']['discovered_tool_names']}")
    print(f"  mcp  resources={c['mcp']['discovered_resource_uris']}")
    print(f"  mcp  call ok={c['mcp']['call_result'].get('ok')}")
    print(f"  lesson: {c['lesson']}")
    assert c["plain"]["must_import_function"] is True
    assert c["mcp"]["must_import_function"] is False
    assert "search_docs" in c["mcp"]["discovered_tool_names"]
    assert c["mcp"]["call_result"].get("ok") is True
    assert "已拆封" in str(c["mcp"]["call_result"].get("content") or "") or "return_policy" in str(
        c["mcp"]["call_result"].get("content") or ""
    ) or "mcp" in str(c["mcp"]["call_result"].get("content") or "")
    print("ASSERT: 发现+调用通；MCP 侧无需 import 业务函数 → PASS")
    note.append("## STEP 3 · 对照\n")
    note.append(f"- plain: `{c['plain']['result'][:300]}`")
    note.append(f"- mcp tools: `{c['mcp']['discovered_tool_names']}`")
    note.append(f"- mcp call: `{c['mcp']['call_result']}`")
    note.append(f"- {c['lesson']}\n")

    # ---- STEP 4 · Tool ≠ Resource ----
    print("\n" + "=" * 52, "STEP 4 · Tool ≠ Resource")
    tv = suite["tool_vs_resource"]
    print(f"  tools={tv['tool_names']} resources={tv['resource_uris']}")
    print(f"  call_ok={tv['call_ok']} read_ok={tv['read_ok']}")
    print(f"  call_resource_as_tool_fails={tv['call_resource_as_tool_fails']}")
    print(f"  rule: {tv['rule']}")
    assert tv["call_ok"] and tv["read_ok"]
    assert tv["call_resource_as_tool_fails"]
    assert "policy://return" in tv["resource_uris"]
    assert "policy://return" not in tv["tool_names"]
    print("ASSERT: 读 Resource ≠ 调 Tool → PASS")
    note.append("## STEP 4 · Tool vs Resource\n")
    note.append(f"- {tv['rule']}\n")

    # ---- STEP 5 · 三问 ----
    print("\n" + "=" * 52, "STEP 5 · 正文三问")
    q = suite["three_questions"]
    print(f"  1 Client: {q['q1_client']}")
    print(f"    Server: {q['q1_server']}")
    print(f"  2 第一个 Tool: {q['q2_first_tool']}")
    print(f"  3 参数: {q['q3_params']}")
    assert q["q2_first_tool"] == suite["first_tool"] == "search_docs"
    assert q["q3_params"]
    print("ASSERT: 模块首个 Tool 已记下 → PASS")
    note.append("## STEP 5 · 三问\n")
    note.append(f"1. Client={q['q1_client']}；Server={q['q1_server']}")
    note.append(f"2. Tool=`{q['q2_first_tool']}`")
    note.append(f"3. 参数=`{q['q3_params']}`\n")

    # ---- STEP 6 · 预告 09.02 ----
    print("\n" + "=" * 52, "STEP 6 · 下一课")
    print("  09.02：把迷你 Server 换成 app/mcp/server.py + 官方 SDK + stdio")
    print("  本课不要求安装 mcp 包；概念验收即可")
    note.append("## STEP 6\n\n- 下一课落地真 MCP Server 进程\n")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: mcp_concepts 验收通过")


if __name__ == "__main__":
    main()
