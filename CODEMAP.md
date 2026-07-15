# ai-service 课次代码索引（M00–M03）

> **规则**：每课源码在独立文件里，文件名带课次编号 `mMM_NN_` 或 `MM_NN_`；**新课只新增，不改旧课文件**。  
> 跟课只认 `app/lessons/` 与 `scripts/MM_NN_*.py`（无编号旧文件已移除）。

## 脚本 `scripts/`

| 课次 | 脚本 |
|------|------|
| 00.04 | `00_04_call_biz_api.py` |
| 00.05 | `00_05_init_milvus.py` |
| 01.01 | `01_01_prompt_compare.py` |
| 01.02 | `01_02_call_with_roles.py` |
| 01.03 | `01_03_crispe_compare.py` |
| 01.04 | `01_04_few_shot_faq.py` |
| 01.05 | `01_05_structured_output_demo.py` |
| 01.07 | `01_07_prompt_template_demo.py` |
| 02.02 | `02_02_count_tokens.py` |
| 02.03 | `02_03_embedding_demo.py` |
| 02.04 | `02_04_embed_vs_chat_demo.py` |
| 02.05 | `02_05_context_window_demo.py` |
| 03.01 | `03_01_rag_vs_llm.py` |
| 03.02 | `03_02_rag_pipeline_demo.py` |
| 03.03 | `03_03_splitters_demo.py` |
| 03.04 | `03_04_init_milvus_rag.py`、`03_04_ingest_sample_docs.py` |
| 03.05 | `03_05_retrieve_demo.py` |
| 03.06 | `03_06_qa_chain_demo.py`、`03_06_rag_eval_smoke.py` |
| 04.01 | `04_01_refuse_demo.py` |
| 04.02 | `04_02_reindex_demo.py` |
| 04.03 | `04_03_tenant_isolation_demo.py` |

## 模块 `app/lessons/`

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

## 依赖方向（只许向下 import）

```text
m02_03_embeddings
  → m03_02_splitters → m03_02_ingest / m03_02_retriever / m03_02_qa_chain
  → m03_03_splitters（import m03_02）
  → m03_04_milvus_store / m03_04_ingest
  → m03_05_ingest_batch / m03_05_retriever
  → m03_06_qa_chain（import m03_05 + llm.client）
  → m04_01_qa_chain（import m03_06；加闸门）
  → m04_02_reindex（import m03_03/04/05；增量替换）
  → m04_03_tenant_store（租户过滤；不改 m03_05）
```

## 基础设施（不按课拆分）

| 路径 | 课次 |
|------|------|
| `app/main.py` | 00.02 |
| `app/config.py` | 00.03 |
| `app/llm/client.py` | 01.x 共用 |
| `app/prompts/*.md` | 01.x 各课 |
| `app/models/schemas.py` | 01.05 |

## 兼容包（勿跟课改）

`app/rag/`、`app/chains/` 仅从 `app/lessons/` re-export，供旧 import 路径使用。
