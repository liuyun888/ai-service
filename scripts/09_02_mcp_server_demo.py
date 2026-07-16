# scripts/09_02_mcp_server_demo.py
"""09.02 搭建 MCP Server 演示。

【本课要感受的三件事】
1. mcp 依赖可 import；app.mcp.server 可加载
2. 进程内 list_tools 能看到 search_docs
3. 真 stdio 拉起子进程后 tools/list + mock call 通；日志走 stderr

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

from app.lessons.m09_02_mcp_server import lesson_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "mcp_server_result.md"
CONFIG_PATH = ROOT / "notes" / "cursor_mcp_ai_service_tools.json"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("MCP Server = 可被 Client 拉起的工具箱进程（stdio）")
    print("ROOT =", ROOT)

    suite = lesson_suite()
    note: list[str] = [
        "# 09.02 搭建 MCP Server · 实跑记录\n",
        "",
        f"- lifecycle: {suite['lifecycle']}",
        "",
    ]

    # ---- STEP 1 · 进程模型 ----
    print("\n" + "=" * 52, "STEP 1 · 进程模型")
    for row in suite["process_models"]:
        print(f"  [{row['mode']}] {row['how']} → {row['fit']}")
    assert {r["mode"] for r in suite["process_models"]} >= {"stdio", "HTTP/SSE"}
    print("ASSERT: stdio / HTTP 两种模型能区分 → PASS")
    note.append("## STEP 1 · 进程模型\n")
    for row in suite["process_models"]:
        note.append(f"- **{row['mode']}**：{row['how']}（{row['fit']}）")
    note.append("")

    # ---- STEP 2 · 依赖与 import ----
    print("\n" + "=" * 52, "STEP 2 · 依赖与 import")
    imp = suite["import"]
    print(f"  mcp_package_ok={imp['mcp_package_ok']}")
    print(f"  server_import_ok={imp['server_import_ok']} name={imp.get('server_name')}")
    if not imp["ok"]:
        print("  HINT: .venv/bin/python -m pip install 'mcp>=1.0'")
        print("  mcp_error:", imp.get("mcp_error"))
        print("  server_error:", imp.get("server_error"))
    assert imp["ok"], imp
    print("ASSERT: mcp + app.mcp.server 可 import → PASS")
    note.append("## STEP 2 · import\n")
    note.append(f"- `{imp}`\n")

    # ---- STEP 3 · 进程内 list ----
    print("\n" + "=" * 52, "STEP 3 · 进程内 tools/list")
    ip = suite["inprocess"]
    print(f"  tools: {ip['tool_names']}")
    for s in ip["schemas"]:
        print(f"    - {s['name']}: {s['description'][:60]} required={s['required']}")
    assert ip["has_search_docs"]
    print("ASSERT: 能 list 到 search_docs → PASS")
    note.append("## STEP 3 · inprocess list\n")
    note.append(f"- tools: `{ip['tool_names']}`\n")

    # ---- STEP 4 · stdio 真拉起 ----
    print("\n" + "=" * 52, "STEP 4 · stdio 子进程握手 + list/call")
    st = suite["stdio"]
    print(f"  command: {st['command']}")
    print(f"  args: {st['args']} cwd={st['cwd']}")
    print(f"  tools: {st['tool_names']}")
    print(f"  call: {st.get('call_texts')}")
    assert st["has_search_docs"]
    assert st["call_alive"]
    print("ASSERT: stdio list + mock call 通 → PASS")
    note.append("## STEP 4 · stdio\n")
    note.append(f"- tools: `{st['tool_names']}`")
    note.append(f"- call: `{st.get('call_texts')}`\n")

    # ---- STEP 5 · stderr 纪律 ----
    print("\n" + "=" * 52, "STEP 5 · 勿污染 stdout")
    sc = suite["stderr_check"]
    print(f"  log_uses_stderr={sc['log_uses_stderr']} ok={sc['ok']}")
    assert sc["ok"]
    print("ASSERT: server.log 走 stderr → PASS")
    note.append("## STEP 5 · stderr\n")
    note.append(f"- `{sc}`\n")

    # ---- STEP 6 · Cursor 配置 ----
    print("\n" + "=" * 52, "STEP 6 · Cursor MCP 配置片段")
    cfg = suite["cursor_config"]
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  已写入:", CONFIG_PATH)
    assert "ai-service-tools" in cfg["mcpServers"]
    assert cfg["mcpServers"]["ai-service-tools"]["args"] == ["-m", "app.mcp.server"]
    print("ASSERT: 配置指向 venv python + -m app.mcp.server → PASS")
    note.append("## STEP 6 · Cursor 配置\n")
    note.append(f"- 文件: `{CONFIG_PATH}`")
    note.append("```json")
    note.append(json.dumps(cfg, ensure_ascii=False, indent=2))
    note.append("```\n")

    assert suite.get("ok") is True
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: mcp_server 验收通过")


if __name__ == "__main__":
    main()
