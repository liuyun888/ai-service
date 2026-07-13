# scripts/03_05_retrieve_demo.py
"""03.05 相似度检索演示：多文档入库 → 3 个问题 topK 检索 → 人工验收排序。

【本课要感受的三件事】
1. 问题文本 → Embedding → 与库中各块算余弦相似度 → 取 topK
2. topK 调大/调小：漏召回 vs 噪声进 Prompt 的权衡
3. 用业务味问题验证「相关文档排在前面」

不覆盖 03.02 已有 m03_02_retriever.py，只调用 retrieve + 本课追加的格式化工具。
03.04 接 Milvus 后，retrieve 内部换成 ANN search，在线调用方式不变。
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m03_02_ingest import build_index  # noqa: E402
from app.lessons.m03_05_ingest_batch import chunks_from_markdown_dir  # noqa: E402
from app.lessons.m03_05_retriever import format_hit, retrieve  # noqa: E402

# ======================== 可调开关 ========================

TOP_K = 4

# memory = 03.02 内存索引（零 Milvus 依赖）；milvus = 03.04 入库后检索
INDEX_BACKEND = os.getenv("INDEX_BACKEND", "memory").strip().lower()

# 多文档样例库（5 份虚构业务文档，与 03.04 ingest 共用）
SAMPLE_DIR = ROOT / "samples" / "docs"

# 3 个业务味问题 + 期望 top1 应来自哪个文件（人工验收参考答案）
@dataclass
class ProbeQuestion:
    """一道探针问题及其期望的「最相关来源文件」。"""

    question: str
    expect_source: str
    expect_keywords: tuple[str, ...]


PROBES: list[ProbeQuestion] = [
    ProbeQuestion(
        question="七天无理由退货需要什么条件？",
        expect_source="return_policy.md",
        expect_keywords=("七天", "7", "无理由", "退货"),
    ),
    ProbeQuestion(
        question="订单一般几天能发货？",
        expect_source="shipping_faq.md",
        expect_keywords=("发货", "16:00", "工作日"),
    ),
    ProbeQuestion(
        question="选修数据结构需要先修哪些课？",
        expect_source="course_enrollment.md",
        expect_keywords=("先修", "CS101", "数据结构"),
    ),
]


def main() -> None:
    if not SAMPLE_DIR.is_dir():
        raise FileNotFoundError(f"请先准备样例目录：{SAMPLE_DIR}")

    print("=" * 52, "CONFIG")
    print("sample_dir:", SAMPLE_DIR)
    print("index_backend:", INDEX_BACKEND)
    print("embedding:", default_embedding_model())
    print("top_k:", TOP_K)
    print("probes:", len(PROBES))

    # ---------- Step 1 · 离线 Index ----------
    backend_label = "Milvus · knowledge_base" if INDEX_BACKEND == "milvus" else "内存索引"
    print("\n" + "=" * 52, f"STEP 1 · Index（离线 · {backend_label}）")

    chunks: list = []
    if INDEX_BACKEND == "milvus":
        from app.lessons.m03_04_ingest import connect_milvus_index

        index = connect_milvus_index()
        if index.entity_count == 0:
            raise RuntimeError(
                "Milvus 库为空，请先运行：python scripts/03_04_ingest_sample_docs.py"
            )
        ms_index = 0.0
        print(f"entity_count: {index.entity_count}  model: {index.model}")
        sources = sorted(p.name for p in SAMPLE_DIR.glob("*.md"))
    else:
        t0 = time.perf_counter()
        chunks = chunks_from_markdown_dir(SAMPLE_DIR, strategy="heading")
        index = build_index(chunks)
        ms_index = (time.perf_counter() - t0) * 1000
        sources = sorted({c.source for c in chunks})

    if chunks:
        print(f"文档数: {len(sources)}  总块数: {len(chunks)}  耗时: {ms_index:.0f} ms")
        for name in sources:
            n = sum(1 for c in chunks if c.source == name)
            print(f"  {name}: {n} chunks")
        print(f"索引 model: {index.model}")
        assert len(chunks) >= 10, "样例库块数应足够多，便于感受 topK 排序"
    else:
        print(f"文档数: {len(sources)}  Milvus entities: {index.entity_count}")
    print("ASSERT: 索引就绪 → PASS")

    note: list[str] = [
        "# 03.05 相似度检索 · 三问 topK 对比\n\n",
        f"- 样例目录：`{SAMPLE_DIR}`\n",
        f"- 索引后端：**{INDEX_BACKEND}**\n",
        f"- Embedding：`{default_embedding_model()}`\n",
        f"- top_k：**{TOP_K}**\n\n",
        "## Step 1 · Index\n\n",
    ]
    if chunks:
        note.append(f"- 文档数：{len(sources)}，总块数：**{len(chunks)}**\n\n")
        for name in sources:
            n = sum(1 for c in chunks if c.source == name)
            note.append(f"- `{name}`：{n} chunks\n")
    else:
        note.append(f"- Milvus entities：**{index.entity_count}**\n")
    note.append("\n")

    # ---------- Step 2 · 在线 Retrieve × 3 问 ----------
    all_pass = True
    for i, probe in enumerate(PROBES, start=1):
        print("\n" + "=" * 52, f"STEP 2.{i} · Retrieve")
        print("Q:", probe.question)

        t0 = time.perf_counter()
        hits = retrieve(index, probe.question, top_k=TOP_K)
        ms_ret = (time.perf_counter() - t0) * 1000

        assert hits, f"检索结果不应为空：{probe.question}"
        print(f"top_{TOP_K}（耗时 {ms_ret:.0f} ms）：")
        for rank, (chunk, score) in enumerate(hits):
            print(f"  #{rank + 1}  {format_hit(chunk, score)}")

        top_chunk, top_score = hits[0]
        keyword_ok = any(k in top_chunk.text for k in probe.expect_keywords)
        source_ok = top_chunk.source == probe.expect_source

        if source_ok and keyword_ok:
            print(f"ASSERT: top1 来自 {probe.expect_source} 且含关键词 → PASS")
        else:
            all_pass = False
            print(
                f"WARN: top1={top_chunk.source}，期望 {probe.expect_source}；"
                f"请人工看排序是否合理（Embedding 模型不同可能略有偏差）"
            )

        # 退货问题：食堂菜单不应排第一（验证不会「脏召回」霸榜）
        if probe.expect_source == "return_policy.md":
            assert top_chunk.source != "cafeteria_menu.md", (
                "问退货时，食堂菜单不应排第一"
            )
            print("ASSERT: 退货问题 · 食堂菜单未排第一 → PASS")

        note.append(f"## Q{i} · {probe.question}\n\n")
        note.append(f"期望 top1：`{probe.expect_source}`\n\n")
        for rank, (chunk, score) in enumerate(hits):
            note.append(f"- #{rank + 1} {format_hit(chunk, score, max_len=100)}\n")
        note.append("\n")

    # ---------- Step 3 · topK 对比（同一问，K=2 vs K=5） ----------
    print("\n" + "=" * 52, "STEP 3 · topK 对比")
    q = PROBES[0].question
    for k in (2, 5):
        hits = retrieve(index, q, top_k=k)
        print(f"\ntop_k={k}:")
        for rank, (chunk, score) in enumerate(hits):
            print(f"  #{rank + 1}  {format_hit(chunk, score, max_len=60)}")

    note.append("## topK 对比（同一问：七天无理由退货）\n\n")
    note.append("- **K=2**：块少，Prompt 短，但可能漏召回\n")
    note.append("- **K=5**：召回更全，但噪声块也可能进 Prompt\n\n")

    note.append("## 结论（参考答案）\n\n")
    note.append(
        "- Retrieve = 问题向量化 + 与库中块算相似度 + 取 topK。\n"
        "- 相关文档应排在前面；无关文档（如食堂菜单）不应在业务问题下霸榜。\n"
        f"- 本跑使用索引后端：**{INDEX_BACKEND}**（memory=内存，milvus=03.04 入库后）。\n"
    )

    out = ROOT / "notes" / "retrieve_compare_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(note), encoding="utf-8")
    print(f"\n笔记已写入：{out}")

    if not all_pass:
        print("\n部分探针未严格 PASS，请对照笔记人工确认排序。")


if __name__ == "__main__":
    main()
