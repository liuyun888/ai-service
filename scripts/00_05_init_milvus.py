# scripts/00_05_init_milvus.py
"""课次 00.05 · 向量库连接入门：创建 knowledge_base 空壳（DIM=1024）。

本文件为 00.05 课件原文，后续课次请勿修改。
03.04 RAG 入库请用 scripts/03_04_init_milvus_rag.py。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from pymilvus import DataType, MilvusClient  # noqa: E402

from app.config import MILVUS_HOST, MILVUS_PASSWORD, MILVUS_PORT, MILVUS_USER  # noqa: E402

COLLECTION = "knowledge_base"
DIM = 1024  # 须与后续 Embedding 模型维度一致；本课先建壳


def main() -> None:
    # uri + user/password：开启鉴权的实例必须带账号密码
    client = MilvusClient(
        uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
        user=MILVUS_USER,
        password=MILVUS_PASSWORD,
    )
    print("connected:", MILVUS_HOST, MILVUS_PORT, "user=", MILVUS_USER)

    if client.has_collection(COLLECTION):
        print("already exists:", COLLECTION)
    else:
        schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(
            field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True
        )
        schema.add_field(
            field_name="text", datatype=DataType.VARCHAR, max_length=65535
        )
        schema.add_field(
            field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=DIM
        )
        client.create_collection(collection_name=COLLECTION, schema=schema)
        print("created:", COLLECTION, "dim=", DIM)

    print("collections:", client.list_collections())


if __name__ == "__main__":
    main()
