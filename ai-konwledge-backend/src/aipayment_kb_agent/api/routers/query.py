from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from aipayment_kb_agent.api.dependencies import get_agent
from aipayment_kb_agent.core.agent import KnowledgeAgent
from aipayment_kb_agent.models.request import QueryRequest
from aipayment_kb_agent.models.response import QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    auto_upgrade: bool | None = Query(default=None),
    agent: KnowledgeAgent = Depends(get_agent),
) -> QueryResponse:
    req = payload.model_copy()
    if auto_upgrade is not None:
        req.auto_upgrade = auto_upgrade
    logger.info("api:query session=%s auto_upgrade=%s", req.session_id, req.auto_upgrade)
    return agent.query(req)
