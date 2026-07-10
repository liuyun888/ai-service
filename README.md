# ai-service

跨行业通用 AI 引擎（FastAPI）。

## 快速开始

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` 并填写
4. `uvicorn app.main:app --port 8091 --reload`
5. 打开 http://127.0.0.1:8091/health