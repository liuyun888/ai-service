# scripts/09_04_client_integration_demo.py
"""09.04 客户端接入与选型集成演示（M09 收束）。

【本课要感受的三件事】
1. Cursor 配置可生成；stdio Client 能 list/call（对齐 IDE）
2. 同一 SKU：进程内 / MCP / REST 形结果一致（单实现双入口）
3. README + 选型矩阵写清何时用 MCP / REST / 进程内；Harness 先「仅开发」

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m09_04_client_integration import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "client_integration_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("开发走 MCP，生产进程内；REST 给网关——同一 tools_*.py")
    print("ROOT =", ROOT)

    suite = demo_suite(notes_dir=ROOT / "notes")
    note: list[str] = ["# 09.04 客户端接入与选型集成 · 实跑记录\n", ""]

    # ---- STEP 1 · Cursor 配置 ----
    print("\n" + "=" * 52, "STEP 1 · IDE Client 配置")
    c = suite["cursor"]
    print(f"  path: {c['path']}")
    print(json.dumps(c["config"], ensure_ascii=False, indent=2))
    srv = c["config"]["mcpServers"]["ai-service-tools"]
    assert srv["args"] == ["-m", "app.mcp.server"]
    assert "cwd" in srv and str(srv["cwd"]).endswith("ai-service")
    print("ASSERT: 配置指向 venv 模块入口 → PASS")
    note.append("## STEP 1 · Cursor 配置\n")
    note.append(f"- `{c['path']}`\n")

    # ---- STEP 2 · 选型矩阵 ----
    print("\n" + "=" * 52, "STEP 2 · MCP vs REST vs 进程内")
    for row in suite["matrix"]:
        print(f"  [{row['way']}] {row['best_for']}")
    assert len(suite["matrix"]) == 3
    print("ASSERT: 三扇门齐全 → PASS")
    note.append("## STEP 2 · 选型\n")
    for row in suite["matrix"]:
        note.append(f"- **{row['way']}**：{row['best_for']}；注意：{row['watch']}")
    note.append("")

    # ---- STEP 3 · 场景选择 ----
    print("\n" + "=" * 52, "STEP 3 · 场景 → 选型")
    for s in suite["scenarios"]:
        print(f"  {s['scenario']!r} → {s['pick']} | {s['reason']}")
    picks = {s["pick"] for s in suite["scenarios"]}
    assert "MCP" in picks and "进程内函数" in picks and "REST" in picks
    print("ASSERT: 调试/生产/网关各走一门 → PASS")
    note.append("## STEP 3 · 场景\n")
    for s in suite["scenarios"]:
        note.append(f"- {s['scenario']} → **{s['pick']}**（{s['reason']}）")
    note.append("")

    # ---- STEP 4 · 双入口同一结果 ----
    print("\n" + "=" * 52, "STEP 4 · 双入口（+ REST 形）同一实现")
    d = suite["dual"]
    print(f"  inprocess: {d['inprocess']['result']}")
    print(f"  mcp:       {d['mcp_stdio']['result']}")
    print(f"  rest body: {d['rest_style']['http']['body']}")
    print(f"  same={d['same_implementation_result']}")
    assert d["same_implementation_result"]
    assert "get_inventory" in d["mcp_stdio"]["listed_tools"]
    print("ASSERT: 三入口结果一致且可 list → PASS")
    note.append("## STEP 4 · 双入口\n")
    note.append(f"- inprocess: `{d['inprocess']['result']}`")
    note.append(f"- mcp: `{d['mcp_stdio']['result']}`")
    note.append(f"- rest: `{d['rest_style']['http']}`")
    note.append(f"- {d['lesson']}\n")

    # ---- STEP 5 · Harness 策略 ----
    print("\n" + "=" * 52, "STEP 5 · 接入 Harness")
    h = suite["harness"]
    print(f"  L1: {h['level_1_dev_only']['title']} recommend={h['level_1_dev_only']['recommend']}")
    print(f"  L2: {h['level_2_runtime_client']['title']} recommend={h['level_2_runtime_client']['recommend']}")
    print(f"  → {h['one_liner']}")
    assert h["level_1_dev_only"]["recommend"] is True
    assert h["level_2_runtime_client"]["recommend"] is False
    print("ASSERT: 大多数先「仅开发」→ PASS")
    note.append("## STEP 5 · Harness\n")
    note.append(f"- {h['one_liner']}\n")

    # ---- STEP 6 · README + 安全 + 无双份 ----
    print("\n" + "=" * 52, "STEP 6 · README / 安全 / 无双份逻辑")
    r, sec, nd = suite["readme"], suite["security"], suite["no_dup"]
    print(f"  README exists={r['exists']} missing={r['missing']}")
    print(f"  no_dup ok={nd['ok']} (server 无 MOCK_DB)")
    for item in sec:
        print(f"  - {item['item']}: {item['do']}")
    assert r["ok"]
    assert nd["ok"]
    assert any("只读" in x["do"] for x in sec)
    print("ASSERT: 文档齐全；业务无双份拷贝；只读默认 → PASS")
    note.append("## STEP 6 · 文档与安全\n")
    note.append(f"- README: `{r['path']}`")
    note.append(f"- no_dup: `{nd}`")
    for item in sec:
        note.append(f"- {item['item']}: {item['do']}")
    note.append("")

    assert suite.get("ok") is True
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: client_integration 验收通过（M09 里程碑可勾选）")


if __name__ == "__main__":
    main()
