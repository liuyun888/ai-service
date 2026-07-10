from fastapi import FastAPI
from app.config import APP_NAME

app = FastAPI(title=APP_NAME)

@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}