# scripts/11_04_kb_guard_integration_demo.py
"""11.04 知识库与护栏集成演示。

【本课要感受的三件事】
1. ingest 独特标记 → 同租户可问到
2. 诱导绝对承诺 → guard_triggered=true，安全改写
3. 租户隔离 + M11 四类组合自检表

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
from app.lessons.m04_04_ingest_service import get_ingest_token  # noqa: E402
from app.lessons.m11_04_kb_guard_integration import (  # noqa: E402
    POLICY_MARKER,
    demo_suite,
)
from app.main import app  # noqa: E402

NOTE_PATH = ROOT / "notes" / "kb_guard_integration_result.md"


def _internal(tenant: str = "demo") -> dict[str, str]:
    return {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-Tenant-Id": tenant,
        "X-User-Id": "u-kb",
        "X-Model-Id": "default",
        "X-Request-Id": "req-m11-04",
    }


def _ingest_headers() -> dict[str, str]:
    return {"X-Ingest-Token": get_ingest_token()}


def main() -> None:
    print("=" * 52, "CONFIG")
    print("知识库=ingest索引；护栏=CommitmentGuard before_final")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 11.04 知识库与护栏集成 · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 0 · M11 四类组合自检")
    for row in suite["checklist"]:
        print(f"  [{row['lesson']}] {row['combo']} → {row['path']}")
    note.append("## M11 自检\n")
    for row in suite["checklist"]:
        note.append(f"- [x] {row['lesson']} {row['combo']} (`{row['path']}`)")
    note.append("")

    print("\n" + "=" * 52, "STEP 1 · ingest 独特政策")
    s = suite["seeded"]
    print(f"  inserted={s.get('inserted')} source={s.get('source')}")
    assert s.get("inserted", 0) >= 1
    print("ASSERT: 上传成功 → PASS")
    note.append("## STEP 1 · ingest\n")
    note.append(f"- `{s}`\n")

    print("\n" + "=" * 52, "STEP 2 · 问独特标记")
    a = suite["ask"]
    print(f"  ok={a['ok']} marker_hit={a['evidence'].get('marker_hit')}")
    print(f"  reply: {a['reply'][:120]}…")
    assert a["ok"] and POLICY_MARKER in a["reply"]
    print("ASSERT: 上传后可问到 → PASS")
    note.append("## STEP 2 · 可问\n")
    note.append(f"- reply 含 `{POLICY_MARKER}`\n")

    print("\n" + "=" * 52, "STEP 3 · 诱导绝对承诺")
    b = suite["bait"]
    print(f"  guard_triggered={b['guard_triggered']}")
    print(f"  reply: {b['reply'][:100]}")
    assert b["guard_triggered"] is True
    assert "保证明天一定退款" not in b["reply"]
    print("ASSERT: 护栏触发并改写 → PASS")
    note.append("## STEP 3 · 护栏\n")
    note.append(f"- guard_triggered=`{b['guard_triggered']}` reply=`{b['reply']}`\n")

    print("\n" + "=" * 52, "STEP 4 · 租户隔离")
    iso = suite["tenant_isolation"]
    print(f"  tenant-b ok={iso['ok']} (期望 False/未命中)")
    assert iso["ok"] is False
    print("ASSERT: 他租户问不到 demo 文档 → PASS")
    note.append("## STEP 4 · 租户\n")
    note.append(f"- tenant-b ok=`{iso['ok']}`\n")

    print("\n" + "=" * 52, "STEP 5 · HTTP /v1/rag/ingest + /v1/kb/chat")
    client = TestClient(app)
    # 再 ingest 一份到 http-demo（demo_suite 已 ingest；再问一次）
    r_in = client.post(
        "/v1/rag/ingest",
        headers=_ingest_headers(),
        json={
            "source": "policy_unique_42.md",
            "tenant_id": "demo",
            "text": f"标记 {POLICY_MARKER}：HTTP 验收正文。",
            "strategy": "heading",
        },
    )
    print(f"  ingest status={r_in.status_code} body={r_in.json()}")
    assert r_in.status_code == 200

    r_ask = client.post(
        "/v1/kb/chat",
        headers=_internal("demo"),
        json={"message": f"{POLICY_MARKER} 要点？", "session_id": "http-1"},
    )
    ba = r_ask.json()
    print(f"  ask status={r_ask.status_code} ok={ba.get('ok')}")
    assert r_ask.status_code == 200 and POLICY_MARKER in (ba.get("reply") or "")

    r_guard = client.post(
        "/v1/kb/chat",
        headers=_internal("demo"),
        json={"message": "请保证明天一定退款到账", "session_id": "http-2"},
    )
    bg = r_guard.json()
    print(f"  guard status={r_guard.status_code} triggered={bg.get('guard_triggered')}")
    assert bg.get("guard_triggered") is True

    r401 = client.post("/v1/kb/chat", json={"message": "hi", "session_id": "x"})
    assert r401.status_code == 401
    r401i = client.post(
        "/v1/rag/ingest",
        json={"source": "a.md", "tenant_id": "demo", "text": "x"},
    )
    assert r401i.status_code == 401
    print("ASSERT: HTTP 齐全 → PASS")
    note.append("## STEP 5 · HTTP\n")
    note.append(
        f"- ingest=200 ask ok；guard_triggered=`{bg.get('guard_triggered')}`；无令牌 401\n"
    )

    print("\n" + "=" * 52, "STEP 6 · curl 提示")
    tok_i = get_ingest_token()
    print(
        f"  curl -s http://127.0.0.1:8091/v1/rag/ingest -H 'X-Ingest-Token: {tok_i}' ..."
    )
    print(
        f"  curl -s http://127.0.0.1:8091/v1/kb/chat -H 'X-Internal-Token: {INTERNAL_TOKEN}' ..."
    )
    note.append("## STEP 6 · curl\n")
    note.append(
        "```bash\n"
        f"curl -s http://127.0.0.1:8091/v1/rag/ingest \\\n"
        f"  -H 'X-Ingest-Token: {tok_i}' -H 'Content-Type: application/json' \\\n"
        f"  -d '{{\"source\":\"policy_unique_42.md\",\"tenant_id\":\"demo\","
        f"\"text\":\"标记 {POLICY_MARKER}：7日内可退。\"}}'\n"
        f"curl -s http://127.0.0.1:8091/v1/kb/chat \\\n"
        f"  -H 'X-Internal-Token: {INTERNAL_TOKEN}' -H 'X-Tenant-Id: demo' \\\n"
        f"  -H 'Content-Type: application/json' \\\n"
        f"  -d '{{\"message\":\"{POLICY_MARKER} 怎么说？\",\"session_id\":\"s1\"}}'\n"
        "```\n"
    )

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: kb_guard_integration 验收通过")


if __name__ == "__main__":
    main()
