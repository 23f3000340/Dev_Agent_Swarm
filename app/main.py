# app/main.py
from fastapi import FastAPI
from app.config import settings
from app.core.logger import setup_logging
from app.core.database import init_db
from app.api.v1.endpoints import router as v1_router
from app.core.bedrock_client import BedrockOrchestrator

log = setup_logging(settings.LOG_LEVEL)
app = FastAPI(
    title="DevAgent Swarm API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.APP_NAME}

@app.get("/health/deep")
async def deep_health():
    ok = await BedrockOrchestrator().health_check()
    return {"api": "ok", "bedrock": "ok" if ok else "degraded"}

app.include_router(v1_router, prefix="/api/v1", tags=["analysis"])
