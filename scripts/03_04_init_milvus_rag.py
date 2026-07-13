# scripts/03_04_init_milvus_rag.py
"""03.04 向量化入库：创建/校验 knowledge_base（RAG 版 Schema）。

与 00.05 的 00_05_init_milvus.py 并存：
- 00.05：DIM=1024 最小空壳（id / text / embedding）
- 本脚本：dim 自动读取当前 Embedding 模型，并带 source / section / chunk_id 元数据字段

若你按 00.05 建过 1024 维壳，本脚本或 03_04_ingest_sample_docs.py 会提示维度不一致；
开发期可设 RECREATE_ON_DIM_MISMATCH=True 后 drop 重建。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m02_03_embeddings import default_embedding_model, embedding_dim  # noqa: E402
from app.lessons.m03_04_milvus_store import (  # noqa: E402
    COLLECTION,
    count_entities,
    ensure_knowledge_base_collection,
    get_milvus_client,
)

# 维度与 00.05 壳不一致时是否 drop 重建（开发期 True，生产慎用）
RECREATE_ON_DIM_MISMATCH = True


def main() -> None:
    from app.config import MILVUS_HOST, MILVUS_PORT, MILVUS_USER

    client = get_milvus_client()
    print("connected:", MILVUS_HOST, MILVUS_PORT, "user=", MILVUS_USER)
    print("embedding:", default_embedding_model(), "dim=", embedding_dim())
    print("collection:", COLLECTION)
    print("recreate_on_dim_mismatch:", RECREATE_ON_DIM_MISMATCH)

    existed = client.has_collection(COLLECTION)
    ensure_knowledge_base_collection(client, recreate=RECREATE_ON_DIM_MISMATCH)

    if existed and not RECREATE_ON_DIM_MISMATCH:
        print("already exists:", COLLECTION)
    print("entity_count:", count_entities(client))
    print("collections:", client.list_collections())


if __name__ == "__main__":
    main()
