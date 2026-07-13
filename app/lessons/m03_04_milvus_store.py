# app/lessons/m03_04_milvus_store.py
# 课次 03.04 向量化入库 —— 本文件为课件原文，后续课次请勿修改
"""Milvus 版 Index 存储：chunk → Embedding → knowledge_base Collection。

03.04 专用模块；与 03.02 的 InMemoryIndex 并存，retrieve 按类型自动分流。
建表入口见 scripts/03_04_init_milvus_rag.py（00.05 课件仍用 scripts/00_05_init_milvus.py）。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.lessons.m02_03_embeddings import default_embedding_model, embed_texts, embedding_dim
from app.lessons.m03_03_splitters import Chunk

# 与 00.05 专栏统一命名
COLLECTION = "knowledge_base"


@dataclass
class MilvusIndex:
    """已入库的 Milvus 索引句柄（供 retrieve 使用）。

    :param collection: Collection 名，默认 knowledge_base
    :param model: 建库时用的 Embedding 模型（检索须同一模型）
    :param entity_count: 当前实体条数，便于脚本验收
    """

    collection: str = COLLECTION
    model: str = ""
    entity_count: int = 0


def get_milvus_client():
    """带鉴权连接 Milvus（与 00_05_init_milvus.py / Attu 填法一致）。"""
    from pymilvus import MilvusClient

    from app.config import MILVUS_HOST, MILVUS_PASSWORD, MILVUS_PORT, MILVUS_USER

    return MilvusClient(
        uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
        user=MILVUS_USER,
        password=MILVUS_PASSWORD,
    )


def _collection_vector_dim(client, name: str) -> int | None:
    """从已有 Collection 的 schema 里读出 embedding 维度；不存在则返回 None。"""
    if not client.has_collection(name):
        return None
    desc = client.describe_collection(name)
    for field in desc.get("fields", []):
        if field.get("name") == "embedding":
            params = field.get("params") or field.get("type_params") or {}
            dim = params.get("dim")
            if dim is not None:
                return int(dim)
    return None


def ensure_knowledge_base_collection(
    client=None,
    *,
    recreate: bool = False,
):
    """确保 knowledge_base 存在且 embedding 维度与当前模型一致。

    :param recreate: True 时若维度不匹配则 drop 后重建（开发期常用）
    :raises RuntimeError: 维度不一致且 recreate=False
    """
    from pymilvus import DataType, MilvusClient

    client = client or get_milvus_client()
    want_dim = embedding_dim()

    if client.has_collection(COLLECTION):
        have_dim = _collection_vector_dim(client, COLLECTION)
        if have_dim is not None and have_dim != want_dim:
            msg = (
                f"Collection {COLLECTION} 维度 {have_dim} 与当前模型 {want_dim} 不一致。"
                f"请 drop 后重建，或设 recreate=True"
            )
            if recreate:
                print("WARN:", msg, "→ drop & recreate")
                client.drop_collection(COLLECTION)
            else:
                raise RuntimeError(msg)

    if not client.has_collection(COLLECTION):
        schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(
            field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True
        )
        schema.add_field(
            field_name="text", datatype=DataType.VARCHAR, max_length=65535
        )
        schema.add_field(
            field_name="source", datatype=DataType.VARCHAR, max_length=512
        )
        schema.add_field(
            field_name="section", datatype=DataType.VARCHAR, max_length=512
        )
        schema.add_field(field_name="chunk_id", datatype=DataType.INT64)
        schema.add_field(
            field_name="embedding",
            datatype=DataType.FLOAT_VECTOR,
            dim=want_dim,
        )

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        client.create_collection(
            collection_name=COLLECTION,
            schema=schema,
            index_params=index_params,
        )
        print(f"created: {COLLECTION} dim={want_dim}")

    client.load_collection(COLLECTION)
    return client


def count_entities(client=None) -> int:
    """返回 Collection 内实体条数。"""
    client = client or get_milvus_client()
    if not client.has_collection(COLLECTION):
        return 0
    stats = client.get_collection_stats(COLLECTION)
    return int(stats.get("row_count", 0))


def peek_sample_text(client=None) -> str:
    """抽查一条 text 字段，验收「能读回原文片段」。"""
    client = client or get_milvus_client()
    rows = client.query(
        collection_name=COLLECTION,
        filter="chunk_id >= 0",
        output_fields=["text"],
        limit=1,
    )
    if not rows:
        return ""
    return str(rows[0].get("text", ""))[:120]


def _delete_sources(client, sources: set[str]) -> None:
    """按 source 删旧数据，避免重复跑脚本翻倍（开发期幂等）。"""
    for src in sources:
        # filter 字符串需转义引号
        safe = src.replace('"', '\\"')
        client.delete(collection_name=COLLECTION, filter=f'source == "{safe}"')


def ingest_chunks_to_milvus(
    chunks: list[Chunk],
    *,
    replace_sources: bool = True,
    recreate_on_dim_mismatch: bool = False,
) -> int:
    """chunk 批量 Embedding 并写入 Milvus。

    :param chunks: splitters 产出，须带 source / chunk_id
    :param replace_sources: 写入前按 source 删旧块（同文件改版时常用）
    :return: 本次成功写入条数
    :raises ValueError: chunks 为空
    """
    if not chunks:
        raise ValueError("chunks 不能为空")

    client = ensure_knowledge_base_collection(
        recreate=recreate_on_dim_mismatch
    )

    if replace_sources:
        sources = {c.source for c in chunks if c.source}
        if sources:
            _delete_sources(client, sources)

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)
    if len(vectors) != len(chunks):
        raise ValueError("向量数与 chunk 数不一致")

    rows = [
        {
            "text": chunk.text,
            "source": chunk.source,
            "section": chunk.section,
            "chunk_id": chunk.chunk_id,
            "embedding": vec,
        }
        for chunk, vec in zip(chunks, vectors)
    ]
    client.insert(collection_name=COLLECTION, data=rows)
    client.flush(COLLECTION)
    return len(rows)


def connect_milvus_index() -> MilvusIndex:
    """连接已入库的 Milvus，返回检索句柄。"""
    client = ensure_knowledge_base_collection()
    n = count_entities(client)
    return MilvusIndex(
        collection=COLLECTION,
        model=default_embedding_model(),
        entity_count=n,
    )


def search_milvus(
    index: MilvusIndex,
    query: str,
    *,
    top_k: int = 4,
) -> list[tuple[Chunk, float]]:
    """在 Milvus 里做 ANN 检索，返回与内存版相同结构。"""
    if top_k <= 0:
        raise ValueError("top_k 必须为正数")
    if index.entity_count == 0:
        return []

    client = get_milvus_client()
    q_vec = embed_texts([query])[0]

    raw = client.search(
        collection_name=index.collection,
        data=[q_vec],
        limit=top_k,
        output_fields=["text", "source", "section", "chunk_id"],
        search_params={"metric_type": "COSINE", "params": {}},
    )
    if not raw or not raw[0]:
        return []

    hits: list[tuple[Chunk, float]] = []
    for item in raw[0]:
        entity = item.get("entity") or {}
        chunk = Chunk(
            text=str(entity.get("text", "")),
            chunk_id=int(entity.get("chunk_id", 0)),
            source=str(entity.get("source", "")),
            section=str(entity.get("section", "")),
        )
        # Milvus COSINE 返回的 distance 即相似度，越大越近
        score = float(item.get("distance", 0.0))
        hits.append((chunk, score))
    return hits
