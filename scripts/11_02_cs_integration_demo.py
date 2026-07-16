# scripts/11_02_cs_integration_demo.py
"""11.02 对话客服集成演示。

【本课要感受的四件事】
1. FAQ（物流）自动答，action=reply
2. 投诉 → action=handoff 且 summary 非空
3. 同 session_id 记住运单号
4. 规则/配置与代码分离（cs_config.yaml）

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

from fastapi.testclient import TestClient  # noqa: E402

from app.config import INTERNAL_TOKEN  # noqa: E402
from app.lessons.m11_02_cs_integration import (  # noqa: E402
    DEMO_HANDOFF,
    DEMO_SHIP,
    check_handoff_rules,
    demo_suite,
    load_cs_config,
)
from app.main import app  # noqa: E402

NOTE_PATH = ROOT / "notes" / "cs_integration_result.md"


def _headers(tenant: str = "demo") -> dict[str, str]:
    return {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-Tenant-Id": tenant,
        "X-User-Id": "u-cs",
        "X-Model-Id": "default",
        "X-Request-Id": "req-m11-02",
    }


def main() -> None:
    print("=" * 52, "CONFIG")
    print("客服 = Loop + 记忆 + 转人工；配置 app/agents/cs_config.yaml")
    print("ROOT =", ROOT)

    suite = demo_suite()
    cfg = load_cs_config()
    note: list[str] = ["# 11.02 对话客服集成 · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 0 · 配置文件")
    print(f"  path={suite['config_path']} name={suite['config_name']}")
    assert Path(suite["config_path"]).is_file()
    print("ASSERT: cs_config.yaml 存在 → PASS")
    note.append("## 配置\n")
    note.append(f"- `{suite['config_path']}` name=`{suite['config_name']}`\n")

    print("\n" + "=" * 52, "STEP 1 · 物流 FAQ 自动答")
    s = suite["ship"]
    print(f"  Q: {DEMO_SHIP}")
    print(f"  action={s['action']} tracking={s.get('session_tracking')}")
    print(f"  reply: {s['reply'][:120]}")
    assert s["action"] == "reply" and "转运" in s["reply"]
    print("ASSERT: 自动答无 handoff → PASS")
    note.append("## STEP 1 · 物流\n")
    note.append(f"- action=`{s['action']}` reply=`{s['reply']}`\n")

    print("\n" + "=" * 52, "STEP 2 · 同会话记忆")
    f = suite["follow"]
    print(f"  Q: 到哪了 → tracking={f.get('session_tracking')}")
    assert f["session_tracking"] == "SF123456"
    print("ASSERT: session 记住运单 → PASS")
    note.append("## STEP 2 · 记忆\n")
    note.append(f"- tracking=`{f.get('session_tracking')}`\n")

    print("\n" + "=" * 52, "STEP 3 · 投诉转人工")
    h = suite["handoff"]
    print(f"  Q: {DEMO_HANDOFF}")
    print(f"  action={h['action']} reason={h['reason']}")
    print(f"  summary:\n{h['summary']}")
    assert h["action"] == "handoff" and h["summary"]
    print("ASSERT: handoff + summary → PASS")
    note.append("## STEP 3 · handoff\n")
    note.append(f"- reason=`{h['reason']}`")
    note.append(f"- summary:\n\n```\n{h['summary']}\n```\n")

    print("\n" + "=" * 52, "STEP 4 · 规则函数（连败）")
    t = suite["tool_fail_rule"]
    print(f"  tool_fail → {t}")
    assert t["handoff"] and t["reason"] == "tool_fail"
    # 再测关键词
    kw_ho, kw_r = check_handoff_rules(
        "我要转人工",
        keywords=list(cfg["handoff_rules"]["keywords"]),
    )
    assert kw_ho and kw_r == "user_requested"
    print("ASSERT: 规则可单测 → PASS")
    note.append("## STEP 4 · 规则\n")
    note.append(f"- tool_fail=`{t}` keyword_转人工=`{kw_r}`\n")

    print("\n" + "=" * 52, "STEP 5 · HTTP /v1/cs/chat")
    client = TestClient(app)
    r1 = client.post(
        "/v1/cs/chat",
        headers=_headers(),
        json={"message": DEMO_SHIP, "session_id": "http-cs-1"},
    )
    b1 = r1.json()
    print(f"  ship status={r1.status_code} action={b1.get('action')}")
    assert r1.status_code == 200 and b1.get("action") == "reply"
    r2 = client.post(
        "/v1/cs/chat",
        headers=_headers(),
        json={"message": DEMO_HANDOFF, "session_id": "http-cs-2"},
    )
    b2 = r2.json()
    print(f"  handoff status={r2.status_code} action={b2.get('action')}")
    assert r2.status_code == 200 and b2.get("action") == "handoff" and b2.get("summary")
    r401 = client.post("/v1/cs/chat", json={"message": "hi", "session_id": "x"})
    assert r401.status_code == 401
    print("ASSERT: HTTP 路径齐全 → PASS")
    note.append("## STEP 5 · HTTP\n")
    note.append(f"- ship action=`{b1.get('action')}`")
    note.append(f"- handoff action=`{b2.get('action')}` summary 非空")
    note.append(f"- 无令牌 → `{r401.status_code}`\n")

    print("\n" + "=" * 52, "STEP 6 · curl 提示")
    print("  uvicorn app.main:app --port 8091")
    print(
        "  curl -s http://127.0.0.1:8091/v1/cs/chat "
        "-H 'Content-Type: application/json' "
        f"-H 'X-Internal-Token: {INTERNAL_TOKEN}' -H 'X-Tenant-Id: demo' "
        '-d \'{"message":"我要投诉转人工","session_id":"s1"}\''
    )
    note.append("## STEP 6 · curl\n")
    note.append(
        "```bash\n"
        "curl -s http://127.0.0.1:8091/v1/cs/chat \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        f"  -H 'X-Internal-Token: {INTERNAL_TOKEN}' \\\n"
        "  -H 'X-Tenant-Id: demo' \\\n"
        "  -d '{\"message\":\"我要投诉转人工\",\"session_id\":\"s1\"}'\n"
        "```\n"
    )

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: cs_integration 验收通过")


if __name__ == "__main__":
    main()
