from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.chat_stream import router as chat_stream_router
from app.api.rag import router as rag_router
from app.config import APP_NAME

app = FastAPI(title=APP_NAME)

# 04.04：管理端上传回调 → /rag/ingest
app.include_router(rag_router)
# 06.04：单 Agent 客服 → /agent/chat
app.include_router(agent_router)
# 10.03：SSE 打字机 → /v1/chat/stream
app.include_router(chat_stream_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}
