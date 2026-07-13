# scripts/03_04_ingest_sample_docs.py
"""03.04 向量化入库：samples/docs/ → 切分 → Embedding → Milvus knowledge_base。

与 03.05 03_05_retrieve_demo.py 共用同一份样例库（5 份 md，约 25 chunks）。
入库成功后，可跑：
  INDEX_BACKEND=milvus python scripts/03_05_retrieve_demo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m02_03_embeddings import default_embedding_model, embedding_dim  # noqa: E402
from app.lessons.m03_04_ingest import ingest_paths  # noqa: E402

COLLECTION = "knowledge_base"

# ======================== 可调开关 ========================

# 与 03.05 检索演示共用目录
SAMPLE_ROOT = ROOT / "samples" / "docs"

# 维度与旧 Collection 不一致时是否 drop 重建（开发期 True，生产慎用）
RECREATE_ON_DIM_MISMATCH = True


def main() -> None:
    from app.lessons.m03_04_milvus_store import count_entities as _count_entities
    from app.lessons.m03_04_milvus_store import peek_sample_text as _peek_sample_text

    if not SAMPLE_ROOT.is_dir():
        raise FileNotFoundError(f"请先准备样例目录：{SAMPLE_ROOT}")

    paths = sorted(SAMPLE_ROOT.glob("*.md"))
    if len(paths) < 5:
        raise ValueError(f"样例文件不足 5 个，当前 {len(paths)}：{SAMPLE_ROOT}")

    print("=" * 48, "CONFIG")
    print("collection:", COLLECTION)
    print("embedding:", default_embedding_model())
    print("dim:", embedding_dim())
    print("sample_dir:", SAMPLE_ROOT)
    print("files:", len(paths))

    print("\n" + "=" * 48, "INGEST")
    t0 = time.perf_counter()
    n = ingest_paths(
        paths,
        strategy="heading",
        replace_sources=True,
        recreate_on_dim_mismatch=RECREATE_ON_DIM_MISMATCH,
    )
    ms = (time.perf_counter() - t0) * 1000
    print(f"ingested_chunks: {n}  耗时: {ms:.0f} ms")

    total = _count_entities()
    sample = _peek_sample_text()
    print("entity_count:", total)
    print("sample_text:", sample.replace("\n", " ")[:100], "...")

    assert n >= 20, f"写入块数应 ≥ 20，实际 {n}"
    assert total >= n, f"库内条数 {total} 应 ≥ 本次写入 {n}"
    assert sample, "应能读回至少一条 text"
    print("\nASSERT: 入库成功且可读回 text → PASS")

    note = [
        "# 03.04 向量化入库 · 实跑记录\n\n",
        f"- Collection：`{COLLECTION}`\n",
        f"- Embedding：`{default_embedding_model()}`，dim={embedding_dim()}\n",
        f"- 样例目录：`{SAMPLE_ROOT}`\n",
        f"- 文件数：{len(paths)}\n",
        f"- 本次写入：**{n}** chunks\n",
        f"- 库内总计：**{total}** entities\n",
        f"- 抽查 text：`{sample[:120].replace(chr(10), ' ')}...`\n\n",
        "## 下一步\n\n",
        "```bash\n",
        "INDEX_BACKEND=milvus python scripts/03_05_retrieve_demo.py\n",
        "```\n",
        "\n建表脚本：`python scripts/03_04_init_milvus_rag.py`（03.04）；"
        "00.05 课件仍用 `scripts/00_05_init_milvus.py`（DIM=1024）。\n",
    ]
    out = ROOT / "notes" / "ingest_sample_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(note), encoding="utf-8")
    print(f"笔记已写入：{out}")


if __name__ == "__main__":
    main()
