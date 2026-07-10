# scripts/init_milvus.py
# 使用官方推荐的 MilvusClient（ORM 风格 connections/Collection 将在 3.1 移除）
from pymilvus import MilvusClient, DataType

from app.config import MILVUS_HOST, MILVUS_PORT, MILVUS_USER, MILVUS_PASSWORD

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
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=DIM)
        client.create_collection(collection_name=COLLECTION, schema=schema)
        print("created:", COLLECTION)

    print("collections:", client.list_collections())


if __name__ == "__main__":
    main()
