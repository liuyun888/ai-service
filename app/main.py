from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.assistant import router as assistant_router
from app.api.assistant_stream import router as assistant_stream_router
from app.api.chat_stream import router as chat_stream_router
from app.api.cs import router as cs_router
from app.api.extract import router as extract_router
from app.api.kb import router as kb_router
from app.api.rag import router as rag_router
from app.api.workflows import router as workflows_router
from app.config import APP_NAME
from app.lifecycle import app_lifespan

app = FastAPI(title=APP_NAME, lifespan=app_lifespan)

# 04.04：管理端上传回调 → /rag/ingest
app.include_router(rag_router)
# 11.04：正文路径别名 → /v1/rag/ingest（与 /rag 同源）
app.include_router(rag_router, prefix="/v1")
# 06.04：单 Agent 客服 → /agent/chat
app.include_router(agent_router)
# 10.03：SSE 打字机 mock → /v1/chat/stream（教学保留）
app.include_router(chat_stream_router)
# 11.01：业务助手 → /v1/assistant/chat
app.include_router(assistant_router)
# 11.05：统一助手 SSE → /v1/assistant/stream（BFF /chat 正式入口）
app.include_router(assistant_stream_router)
# 11.02：对话客服 → /v1/cs/chat
app.include_router(cs_router)
# 11.03：退货工作流 → /v1/workflows/return/*
app.include_router(workflows_router)
# 11.04：知识库问答+护栏 → /v1/kb/chat
app.include_router(kb_router)
# 12.03：抽取编排 → /v1/extract/invoice
app.include_router(extract_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}
