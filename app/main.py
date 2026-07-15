from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.rag import router as rag_router
from app.config import APP_NAME

app = FastAPI(title=APP_NAME)

# 04.04：管理端上传回调 → /rag/ingest
app.include_router(rag_router)
# 06.04：单 Agent 客服 → /agent/chat
app.include_router(agent_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}
