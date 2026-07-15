# app/lessons — 课次源码（跟文档改这里）

每课一个独立文件，命名 `m模块_课次_简述.py`。后续课**只新增、不改旧课文件**。

| 课次 | 文件 | 说明 |
|------|------|------|
| 02.03 | `m02_03_embeddings.py` | Embedding / cosine |
| 03.02 | `m03_02_splitters.py` | Chunk、固定/标题切分 |
| 03.02 | `m03_02_ingest.py` | 内存索引 build_index |
| 03.02 | `m03_02_retriever.py` | 内存 topK |
| 03.02 | `m03_02_qa_chain.py` | Augment + Generate |
| 03.03 | `m03_03_splitters.py` | section、对比工具（import 03.02） |
| 03.04 | `m03_04_milvus_store.py` | Milvus 建表/写入/ANN |
| 03.04 | `m03_04_ingest.py` | ingest_paths |
| 03.05 | `m03_05_ingest_batch.py` | 多文档 batch 切分 |
| 03.05 | `m03_05_retriever.py` | Milvus+内存统一 retrieve |
| 03.06 | `m03_06_qa_chain.py` | 编号 Augment + 带引用问答 |
| 04.01 | `m04_01_qa_chain.py` | 拒答闸门（低分短路） |
| 04.02 | `m04_02_reindex.py` | 切片边界诊断 + 按 source reindex |
| 04.03 | `m04_03_tenant_store.py` | 租户 metadata 隔离检索 |
| 04.04 | `m04_04_ingest_service.py` | 上游触发同步 ingest |

演示脚本在 `scripts/MM_NN_*.py`，完整索引见仓库根 `CODEMAP.md`。
