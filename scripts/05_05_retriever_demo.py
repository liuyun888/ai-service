# scripts/05_05_retriever_demo.py
"""05.05 Retriever 抽象演示。

【本课要感受的三件事】
1. r.invoke("问题") → list[Document]，与底层是内存还是租户过滤无关
2. metadata 带上 source / score（租户场景还有 tenant_id）
3. TenantIndex 缺 tenant_id → 与 04.03 一样直接报错

工作目录：必须在 ai-service/ 下（ls app/chains/ ，不要写成 ls ai-service/app/...）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from langchain_core.documents import Document  # noqa: E402

from app.chains.knowledge_retriever import KnowledgeRetriever, docs_preview  # noqa: E402
from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m03_05_ingest_batch import chunks_from_markdown_dir  # noqa: E402
from app.lessons.m03_02_ingest import build_index  # noqa: E402
from app.lessons.m04_03_tenant_store import (  # noqa: E402
    TenantIndex,
    build_index_from_tenant_roots,
)

# ======================== 可调开关 ========================

TOP_K = int(os.getenv("TOP_K", "4"))
QUERY = os.getenv("RETRIEVER_QUERY", "七天无理由退货需要什么条件？")
SAMPLE_DIR = ROOT / "samples" / "docs"
TENANT_ROOT = ROOT / "samples" / "tenants"
NOTE_PATH = ROOT / "notes" / "retriever_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("embedding:", default_embedding_model())
    print("top_k:", TOP_K)
    print("query:", QUERY)
    print("sample_dir:", SAMPLE_DIR)
    print("tenant_root:", TENANT_ROOT)
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    if not SAMPLE_DIR.is_dir():
        raise FileNotFoundError(f"缺少样例库：{SAMPLE_DIR}")

    note: list[str] = [
        "# 05.05 Retriever 抽象 · 实跑记录\n",
        f"- query: `{QUERY}`",
        f"- top_k: `{TOP_K}`",
        f"- embedding: `{default_embedding_model()}`",
        "",
    ]

    # ---- STEP 1 · 单库内存索引 → KnowledgeRetriever ----
    print("\n" + "=" * 52, "STEP 1 · 内存索引 + Retriever.invoke")
    chunks = chunks_from_markdown_dir(SAMPLE_DIR)
    mem_index = build_index(chunks)
    r = KnowledgeRetriever(index=mem_index, top_k=TOP_K)
    docs = r.invoke(QUERY)
    assert isinstance(docs, list) and docs, "应返回非空 Document 列表"
    assert all(isinstance(d, Document) for d in docs)
    assert all("source" in (d.metadata or {}) for d in docs)
    assert all("score" in (d.metadata or {}) for d in docs)
    for line in docs_preview(docs):
        print(line)
    # 退货问题应优先打到 return_policy
    top_src = str(docs[0].metadata.get("source", ""))
    print("top1 source:", top_src)
    assert "return" in top_src.lower() or "退" in docs[0].page_content or "七天" in docs[0].page_content
    print("ASSERT: invoke → Document[] 且含 source/score → PASS")
    note.append("## STEP 1 · 单库\n")
    note.extend(f"- {ln}" for ln in docs_preview(docs))
    note.append("")

    # ---- STEP 2 · 缺 tenant_id（TenantIndex）必须报错 ----
    print("\n" + "=" * 52, "STEP 2 · TenantIndex 缺 tenant_id")
    if not TENANT_ROOT.is_dir():
        print("跳过：无 samples/tenants（请先完成 04.03）")
        note.append("## STEP 2 · 跳过（无 tenants 样例）\n")
    else:
        t_index = build_index_from_tenant_roots(
            {
                "tenant_a": TENANT_ROOT / "tenant_a",
                "tenant_b": TENANT_ROOT / "tenant_b",
            }
        )
        assert isinstance(t_index, TenantIndex)
        bad = KnowledgeRetriever(index=t_index, top_k=TOP_K, tenant_id="")
        try:
            bad.invoke(QUERY)
            raise AssertionError("缺 tenant_id 应抛 ValueError")
        except ValueError as exc:
            print("caught:", exc)
            assert "tenant_id" in str(exc)
            print("ASSERT: 缺 tenant → ValueError（04.03 同款）→ PASS")
            note.append("## STEP 2 · 缺 tenant\n")
            note.append(f"- `{exc}`\n")

        # ---- STEP 3 · 带 tenant 隔离检索 ----
        print("\n" + "=" * 52, "STEP 3 · tenant_a / tenant_b 隔离")
        docs_a = KnowledgeRetriever(
            index=t_index, tenant_id="tenant_a", top_k=TOP_K
        ).invoke(QUERY)
        docs_b = KnowledgeRetriever(
            index=t_index, tenant_id="tenant_b", top_k=TOP_K
        ).invoke(QUERY)
        for label, ds in (("tenant_a", docs_a), ("tenant_b", docs_b)):
            print(f"[{label}]")
            for line in docs_preview(ds):
                print(" ", line)
            assert ds, f"{label} 应有命中"
            assert all(d.metadata.get("tenant_id") == label for d in ds)
        print("ASSERT: 各租户 Document.metadata.tenant_id 全正确 → PASS")
        note.append("## STEP 3 · 租户隔离\n")
        note.append("### tenant_a\n")
        note.extend(f"- {ln}" for ln in docs_preview(docs_a))
        note.append("### tenant_b\n")
        note.extend(f"- {ln}" for ln in docs_preview(docs_b))
        note.append("")

    note.append("## 结论\n")
    note.append("- Retriever = 统一插头：`invoke(query) → list[Document]`。")
    note.append("- 适配器内部可换内存 / Milvus / 租户过滤，链代码下节课不用改。")
    note.append("- Document.metadata 至少保留 source、score；租户场景加 tenant_id。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: retriever 验收通过")


if __name__ == "__main__":
    main()
