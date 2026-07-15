# scripts/04_02_reindex_demo.py
"""04.02 切片边界 + 按 source 增量 reindex 完整演示。

【本课要感受的两件事】
1. 固定字数切会把表格/步骤拦腰斩；按标题切更完整
2. 文档改「7→3 个工作日」后，必须 delete(source)+再写入，检索才会变

默认走内存索引（零 Milvus 依赖）。可选：
  INDEX_BACKEND=milvus python scripts/04_02_reindex_demo.py
（需先能连上 knowledge_base）
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m03_03_splitters import (  # noqa: E402
    compare_strategies,
    format_chunk_preview,
)
from app.lessons.m03_05_retriever import retrieve  # noqa: E402
from app.lessons.m04_02_reindex import (  # noqa: E402
    diagnose_cut_boundary,
    reindex_file_memory,
    reindex_file_milvus,
    seed_index_from_dir,
    write_policy_version,
)

# ======================== 可调开关 ========================

INDEX_BACKEND = os.getenv("INDEX_BACKEND", "memory").strip().lower()
BOUNDARY_DOC = ROOT / "samples" / "reindex" / "broken_boundary.md"
WORKDIR = ROOT / "samples" / "reindex" / "workdir"
POLICY_FILE = WORKDIR / "refund_arrival.md"
NOTE_PATH = ROOT / "notes" / "reindex_boundary_result.md"

QUESTION = "退款审核通过后几个工作日到账？"
OLD_DAYS = 7
NEW_DAYS = 3


def _fmt_hit(chunk, score: float, *, max_len: int = 72) -> str:
    """兼容 03.02 Chunk（无 section）与 03.03 Chunk 的一行预览。"""
    section = getattr(chunk, "section", "") or ""
    meta = f"[{section}] " if section else ""
    preview = chunk.text[:max_len].replace("\n", " ")
    suffix = "..." if len(chunk.text) > max_len else ""
    return f"{score:.4f}  {chunk.source}  chunk {chunk.chunk_id}  {meta}{preview}{suffix}"


def _preview_strategies(text: str) -> list[str]:
    """打印 fixed vs heading 的块预览，供笔记引用。"""
    lines: list[str] = []
    cmp = compare_strategies(text, source=BOUNDARY_DOC.name, fixed_size=90, fixed_overlap=10)
    lines.append(f"fixed 块数={len(cmp.fixed)}  heading 块数={len(cmp.heading)}")
    print(f"fixed 块数={len(cmp.fixed)}  heading 块数={len(cmp.heading)}")
    print("\n--- fixed（易切断）前 4 块 ---")
    for c in cmp.fixed[:4]:
        prev = format_chunk_preview(c, max_len=90)
        print(f"  {prev}")
        lines.append(f"- fixed: {prev}")
    print("\n--- heading（按 ##）全部 ---")
    for c in cmp.heading:
        prev = format_chunk_preview(c, max_len=90)
        print(f"  {prev}")
        lines.append(f"- heading: {prev}")
    return lines


def main() -> None:
    if not BOUNDARY_DOC.is_file():
        raise FileNotFoundError(f"缺少切边界样例：{BOUNDARY_DOC}")

    print("=" * 52, "CONFIG")
    print("embedding:", default_embedding_model())
    print("index_backend:", INDEX_BACKEND)
    print("boundary_doc:", BOUNDARY_DOC)
    print("policy_file:", POLICY_FILE)
    print("question:", QUESTION)

    note: list[str] = [
        "# 04.02 切片边界与增量索引 · 实跑记录\n",
        f"- Embedding：`{default_embedding_model()}`",
        f"- 后端：`{INDEX_BACKEND}`",
        f"- 问题：{QUESTION}",
        "",
    ]

    # ==================== STEP 1 · 切片边界 ====================
    print("\n" + "=" * 52, "STEP 1 · 切片边界：fixed vs heading")
    text = BOUNDARY_DOC.read_text(encoding="utf-8")
    note.append("## STEP 1 · 切片边界\n")
    note.extend(_preview_strategies(text))
    note.append("")

    issues = diagnose_cut_boundary(text, source=BOUNDARY_DOC.name)
    print("\n诊断到的症状：")
    if not issues:
        print("  （未命中预设规则，请人工看 fixed 预览是否半截表）")
        note.append("- 诊断：未命中自动规则，请人工看 fixed 预览\n")
    else:
        for iss in issues:
            print(f"  [{iss.strategy}] chunk {iss.chunk_id}: {iss.symptom}")
            print(f"       {iss.preview}")
            note.append(f"- **{iss.strategy}** chunk {iss.chunk_id}: {iss.symptom}")
            note.append(f"  - `{iss.preview}`")
        note.append("")

    # 硬验收：fixed 应至少挖出一个症状；heading 应对「7 个工作日」整段可命中
    assert any(i.strategy == "fixed" for i in issues) or "| 质量问题" in text, (
        "请确认 broken_boundary.md 含表格，便于演示切断"
    )
    heading_ok = any("7 个工作日" in c.text for c in compare_strategies(
        text, source=BOUNDARY_DOC.name
    ).heading)
    assert heading_ok, "按标题切应能保留『7 个工作日』完整句"
    print("ASSERT: heading 保留完整到账句 → PASS")
    if any(i.strategy == "fixed" for i in issues):
        print("ASSERT: fixed 暴露切断症状 → PASS")
    else:
        print("WARN: 自动诊断未标 fixed 症状，请对照预览人工确认")

    # ==================== STEP 2 · 旧版入库 ====================
    print("\n" + "=" * 52, f"STEP 2 · 写入旧版政策（{OLD_DAYS} 个工作日）并检索")
    write_policy_version(POLICY_FILE, days=OLD_DAYS)

    if INDEX_BACKEND == "milvus":
        from app.lessons.m03_04_milvus_store import connect_milvus_index

        info = reindex_file_milvus(POLICY_FILE, strategy="heading")
        index = connect_milvus_index()
        print(f"reindex milvus: {info}")
    else:
        # 工作目录可能只有这一份；再带上 boundary 样例凑「多文档」氛围
        # 先清空 workdir 外的干扰：本步只索引 policy + boundary 拷贝说明
        WORKDIR.mkdir(parents=True, exist_ok=True)
        # 用 seed：workdir 里目前只有 policy；边界样例另放不进同一索引也行
        index = seed_index_from_dir(WORKDIR)
        info = {
            "source": POLICY_FILE.name,
            "deleted": 0,
            "inserted": sum(
                1 for it in index.items if it.chunk.source == POLICY_FILE.name
            ),
            "remain": sum(
                1 for it in index.items if it.chunk.source == POLICY_FILE.name
            ),
        }
        print(f"memory index chunks: {len(index.items)}  policy={info}")

    t0 = time.perf_counter()
    hits_old = retrieve(index, QUESTION, top_k=3)
    print(f"retrieve 耗时 {(time.perf_counter() - t0) * 1000:.0f} ms")
    for i, (chunk, score) in enumerate(hits_old, start=1):
        print(f"  #{i}  {_fmt_hit(chunk, score)}")

    top_old = hits_old[0][0].text if hits_old else ""
    assert f"{OLD_DAYS} 个工作日" in top_old, f"旧版应召回「{OLD_DAYS} 个工作日」"
    print(f"ASSERT: 旧版 top1 含「{OLD_DAYS} 个工作日」→ PASS")

    note.append("## STEP 2 · 旧版检索\n")
    note.append(f"- 文件写入：`{OLD_DAYS} 个工作日`")
    note.append(f"- top1: {_fmt_hit(*hits_old[0]) if hits_old else '(empty)'}")
    note.append("")

    # ==================== STEP 3 · 改文件 + reindex ====================
    print("\n" + "=" * 52, f"STEP 3 · 改成 {NEW_DAYS} 个工作日并 reindex")
    write_policy_version(POLICY_FILE, days=NEW_DAYS)
    print(f"已改写文件: {POLICY_FILE}")

    if INDEX_BACKEND == "milvus":
        info2 = reindex_file_milvus(POLICY_FILE, strategy="heading")
        from app.lessons.m03_04_milvus_store import connect_milvus_index

        index = connect_milvus_index()
    else:
        info2 = reindex_file_memory(index, POLICY_FILE, strategy="heading")
    print(f"reindex: deleted={info2['deleted']} inserted={info2['inserted']} "
          f"remain={info2['remain']}")
    assert info2["deleted"] >= 1, "改版前应已有旧块可删"
    assert info2["inserted"] >= 1, "应写入新块"
    assert info2["remain"] == info2["inserted"], "删净再写后 remain 应等于 inserted"
    print("ASSERT: delete + insert 数量合理 → PASS")

    note.append("## STEP 3 · reindex\n")
    note.append(
        f"- deleted={info2['deleted']} inserted={info2['inserted']} "
        f"remain={info2['remain']}"
    )
    note.append("")

    # ==================== STEP 4 · 新版检索 ====================
    print("\n" + "=" * 52, "STEP 4 · 同问再检索（期望变为 3）")
    hits_new = retrieve(index, QUESTION, top_k=3)
    for i, (chunk, score) in enumerate(hits_new, start=1):
        print(f"  #{i}  {_fmt_hit(chunk, score)}")

    top_new = hits_new[0][0].text if hits_new else ""
    assert f"{NEW_DAYS} 个工作日" in top_new, f"新版 top1 应含「{NEW_DAYS} 个工作日」"
    assert f"{OLD_DAYS} 个工作日" not in top_new, "新版 top1 不应再残留旧到账天数"
    print(f"ASSERT: 新版 top1 含「{NEW_DAYS} 个工作日」且无旧数 → PASS")

    note.append("## STEP 4 · 新版检索\n")
    note.append(f"- top1: {_fmt_hit(*hits_new[0]) if hits_new else '(empty)'}")
    note.append("")
    note.append("## 结论\n")
    note.append("- 切片：fixed 易切断表格/步骤；heading 按小节保留更稳。")
    note.append("- 增量：按 source 先删后写；改文件不 reindex = 幽灵旧知识。")
    note.append(f"- 本跑验证：到账时效 {OLD_DAYS} → {NEW_DAYS} 已反映在检索 top1。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: 切片边界 + 增量 reindex 验收通过")


if __name__ == "__main__":
    main()
