from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from aipayment_kb_agent.api.dependencies import get_agent
from aipayment_kb_agent.api.routers import admin, query, upgrade
from aipayment_kb_agent.config.settings import get_settings
from aipayment_kb_agent.utils.logging import configure_logging

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
def warmup_services() -> None:
    try:
        agent = get_agent()
        agent.embedder.warmup()
        logger.info("startup:warmup_success model=%s", settings.embedding_model)
    except Exception:
        logger.exception("startup:warmup_failed")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    logger.info("request:start id=%s method=%s path=%s", request_id, request.method, request.url.path)
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request:end id=%s status=%s duration_ms=%s",
        request_id,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "env": settings.app_env}


app.include_router(query.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(upgrade.router, prefix=settings.api_prefix)
