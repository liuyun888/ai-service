# scripts/04_04_ingest_api_demo.py
"""04.04 上下游对接 ingest 演示：用 TestClient 模拟管理端回调。

【本课要感受的三件事】
1. 无 Token → 401；空 text → 400（失败可见）
2. POST /rag/ingest 后可用 GET /rag/search 搜到新内容
3. 同一 source 再传新版 = 先删后写（幂等），不会堆两份旧+新

不需先手动起 uvicorn；脚本内 TestClient 直连 app。
若要真 HTTP，另开终端：uvicorn app.main:app --port 8001
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

from fastapi.testclient import TestClient  # noqa: E402

from app.lessons.m04_04_ingest_service import get_ingest_token, reset_store  # noqa: E402
from app.main import app  # noqa: E402

# ======================== 可调开关 ========================

NOTE_PATH = ROOT / "notes" / "ingest_api_result.md"
TENANT = "tenant_a"
SOURCE = "return_policy.md"
QUESTION = "审核通过后几个工作日到账？"


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Ingest-Token": get_ingest_token(),
    }


def main() -> None:
    reset_store()
    client = TestClient(app)
    token = get_ingest_token()

    print("=" * 52, "CONFIG")
    print("tenant:", TENANT)
    print("source:", SOURCE)
    print("token_set:", bool(token))
    print("question:", QUESTION)

    note: list[str] = [
        "# 04.04 上下游对接 ingest · 实跑记录\n",
        f"- tenant: `{TENANT}`",
        f"- source: `{SOURCE}`",
        f"- 问题：{QUESTION}",
        "",
    ]

    # ---- STEP 1 · 鉴权 ----
    print("\n" + "=" * 52, "STEP 1 · 无 Token 应 401")
    r = client.post(
        "/rag/ingest",
        json={"source": SOURCE, "tenant_id": TENANT, "text": "x"},
    )
    print("status:", r.status_code, r.json())
    assert r.status_code == 401
    print("ASSERT: 401 → PASS")
    note.append("## STEP 1 · 鉴权\n")
    note.append(f"- 无 Token → `{r.status_code}`")
    note.append("")

    # ---- STEP 2 · 空正文 ----
    print("\n" + "=" * 52, "STEP 2 · 空 text 应 400")
    r = client.post(
        "/rag/ingest",
        headers=_headers(),
        json={"source": SOURCE, "tenant_id": TENANT, "text": "  "},
    )
    print("status:", r.status_code, r.json())
    assert r.status_code == 400
    print("ASSERT: 400 → PASS")
    note.append("## STEP 2 · 参数校验\n")
    note.append(f"- 空 text → `{r.status_code}` detail=`{r.json().get('detail')}`")
    note.append("")

    # ---- STEP 3 · 首次入库（旧版 7 日）----
    print("\n" + "=" * 52, "STEP 3 · 首次 ingest（7 个工作日）")
    body_v1 = (
        "# 退款到账说明\n\n"
        "## 到账时效\n\n"
        "审核通过后 **7 个工作日** 到账，节假日顺延。\n"
    )
    r = client.post(
        "/rag/ingest",
        headers=_headers(),
        json={
            "source": SOURCE,
            "tenant_id": TENANT,
            "text": body_v1,
            "strategy": "heading",
        },
    )
    print("status:", r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    assert r.status_code == 200
    data1 = r.json()
    assert data1["ok"] and data1["inserted"] >= 1
    assert data1["deleted"] == 0
    print("ASSERT: 首次 inserted>0 deleted=0 → PASS")

    r = client.get(
        "/rag/search",
        headers=_headers(),
        params={"query": QUESTION, "tenant_id": TENANT, "top_k": 2},
    )
    print("search:", r.status_code, r.json())
    assert r.status_code == 200
    hits1 = r.json()["hits"]
    assert hits1 and "7 个工作日" in hits1[0]
    print("ASSERT: 检索到 7 个工作日 → PASS")

    note.append("## STEP 3 · 首次入库\n")
    note.append(f"- 响应：`{json.dumps(data1, ensure_ascii=False)}`")
    note.append(f"- 检索 top1：{hits1[0] if hits1 else ''}")
    note.append("")

    # ---- STEP 4 · 同 source 再传新版（幂等）----
    print("\n" + "=" * 52, "STEP 4 · 同 source 再 ingest（3 个工作日，幂等）")
    body_v2 = (
        "# 退款到账说明\n\n"
        "## 到账时效\n\n"
        "审核通过后 **3 个工作日** 到账，节假日顺延。\n"
    )
    r = client.post(
        "/rag/ingest",
        headers=_headers(),
        json={
            "source": SOURCE,
            "tenant_id": TENANT,
            "text": body_v2,
            "strategy": "heading",
        },
    )
    print("status:", r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    assert r.status_code == 200
    data2 = r.json()
    assert data2["deleted"] >= 1, "改版应删掉旧块"
    assert data2["inserted"] >= 1
    assert data2["remain"] == data2["inserted"], "不应新旧并存翻倍"
    print("ASSERT: deleted>=1 且 remain==inserted → PASS")

    r = client.get(
        "/rag/search",
        headers=_headers(),
        params={"query": QUESTION, "tenant_id": TENANT, "top_k": 2},
    )
    hits2 = r.json()["hits"]
    print("search:", hits2)
    assert hits2 and "3 个工作日" in hits2[0]
    assert "7 个工作日" not in hits2[0]
    print("ASSERT: 检索变为 3 且无旧 7 → PASS")

    note.append("## STEP 4 · 幂等改版\n")
    note.append(f"- 响应：`{json.dumps(data2, ensure_ascii=False)}`")
    note.append(f"- 检索 top1：{hits2[0] if hits2 else ''}")
    note.append("")
    note.append("## curl 对照（需先起服务）\n")
    note.append("```bash")
    note.append("uvicorn app.main:app --port 8001")
    note.append(
        "curl -s -X POST http://127.0.0.1:8001/rag/ingest \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        f"  -H 'X-Ingest-Token: {token}' \\\n"
        "  -d '{\"source\":\"return_policy.md\",\"tenant_id\":\"tenant_a\","
        "\"text\":\"审核通过后 **3** 个工作日到账。\"}'"
    )
    note.append("```")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: ingest API 对接验收通过")


if __name__ == "__main__":
    main()
