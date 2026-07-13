# 03.04 向量化入库 · 实跑记录

- Collection：`knowledge_base`
- Embedding：`BAAI/bge-small-zh-v1.5`，dim=512
- 样例目录：`/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/samples/docs`
- 文件数：5
- 本次写入：**25** chunks
- 库内总计：**50** entities
- 抽查 text：`# 员工食堂 · 本周菜单...`

## 下一步

```bash
INDEX_BACKEND=milvus python scripts/03_05_retrieve_demo.py
```

建表脚本：`python scripts/03_04_init_milvus_rag.py`（03.04）；00.05 课件仍用 `scripts/00_05_init_milvus.py`（DIM=1024）。
