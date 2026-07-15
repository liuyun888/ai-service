# ai-service

跨行业通用 AI 引擎（FastAPI）。

## 快速开始

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` 并填写
4. `uvicorn app.main:app --port 8091 --reload`
5. 打开 http://127.0.0.1:8091/health

## 课次代码怎么找？

- **源码**：`app/lessons/mMM_NN_*.py`（见 [`app/lessons/README.md`](./app/lessons/README.md)）
- **演示脚本**：`scripts/MM_NN_*.py`（见 [`scripts/README.md`](./scripts/README.md)）
- **完整对照表**：[`CODEMAP.md`](./CODEMAP.md)

M00–M03 每课独立文件，**新课只新增、不改旧课**。`scripts/` 与 `app/lessons/` 下**仅保留带课次编号的文件**。


配套文稿，免费看，关注公众号：代码到产品