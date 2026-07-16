# ai-service

跨行业通用 AI 引擎（FastAPI）。

## 快速开始

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` 并填写
4. `uvicorn app.main:app --port 8091 --reload`
5. 打开 http://127.0.0.1:8091/health

## Docker Compose（课次 13.01）

```bash
# 在 ai-service/ 下；密钥放 .env（已进 .dockerignore，不会打进镜像）
docker compose up -d --build
curl -f http://127.0.0.1:8091/health
docker compose down
```

- `Dockerfile`：镜像构建；`CMD` 带 `--timeout-graceful-shutdown 20`
- `docker-compose.yml`：端口 **8091**、healthcheck、`stop_grace_period`
- 离线验收（无 Docker 也可）：`python scripts/13_01_compose_demo.py`
- 真起容器验收：`LIVE_COMPOSE=1 python scripts/13_01_compose_demo.py`

## 可观测与成本（课次 13.02）

```bash
python scripts/13_02_observability_cost_demo.py
# 产出：tmp/trace-final.json 、 notes/cost_tuning_note.md
```

速查：[`docs/ops.md`](./docs/ops.md)。迭代口诀：先 Harness → 再数据 → 后模型。

## 课次代码怎么找？

- **源码**：`app/lessons/mMM_NN_*.py`（见 [`app/lessons/README.md`](./app/lessons/README.md)）
- **演示脚本**：`scripts/MM_NN_*.py`（见 [`scripts/README.md`](./scripts/README.md)）
- **完整对照表**：[`CODEMAP.md`](./CODEMAP.md)

M00–M03 每课独立文件，**新课只新增、不改旧课**。`scripts/` 与 `app/lessons/` 下**仅保留带课次编号的文件**。


配套文稿，免费看，关注公众号：代码到产品
