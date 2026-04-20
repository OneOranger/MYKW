from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from aipayment_kb_agent.api.dependencies import get_agent
from aipayment_kb_agent.core.agent import KnowledgeAgent
from aipayment_kb_agent.models.request import (
    TriggerUpgradeRequest,
    UpgradeBatchReviewRequest,
    UpgradeCreateRequest,
    UpgradeReviewRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upgrade", tags=["upgrade"])


@router.get("/review")
def list_pending(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    items = agent.auto_upgrader.list_pending()
    return {"total": len(items), "items": items}


@router.get("/review/{candidate_id}/preview")
def preview_candidate(candidate_id: str, agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    try:
        return agent.auto_upgrader.preview_pending_markdown(candidate_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/review/{candidate_id}")
def review_candidate(
    candidate_id: str,
    payload: UpgradeReviewRequest,
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    try:
        reviewed = agent.auto_upgrader.review(
            candidate_id=candidate_id,
            action=payload.action,
            reviewer=payload.reviewer,
            note=payload.note,
        )
        return {"ok": True, "item": reviewed}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/review/batch")
def review_batch(
    payload: UpgradeBatchReviewRequest,
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    results = []
    for candidate_id in payload.candidate_ids:
        try:
            item = agent.auto_upgrader.review(
                candidate_id=candidate_id,
                action=payload.action,
                reviewer=payload.reviewer,
                note=payload.note,
            )
            results.append({"candidate_id": candidate_id, "ok": True, "item": item})
        except FileNotFoundError:
            results.append({"candidate_id": candidate_id, "ok": False, "error": "not_found"})
    success = sum(1 for row in results if row["ok"])
    return {"ok": True, "success": success, "failed": len(results) - success, "results": results}


@router.post("/trigger")
def trigger_upgrade(
    payload: TriggerUpgradeRequest,
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    session_msgs = agent.memory.short_term.get(payload.session_id)
    assistant_msgs = [m for m in session_msgs if m.get("role") == "assistant"]
    user_msgs = [m for m in session_msgs if m.get("role") == "user"]
    if not assistant_msgs or not user_msgs:
        return {"ok": False, "message": "No upgradable Q&A found in this session."}
    question = user_msgs[-1]["content"]
    answer = assistant_msgs[-1]["content"]
    items = agent.auto_upgrader.create_candidates(question=question, answer=answer)
    return {"ok": True, "generated": len(items), "items": items}


@router.post("/create")
def create_from_text(
    payload: UpgradeCreateRequest,
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    items = agent.auto_upgrader.create_candidates(question=payload.question, answer=payload.answer)
    return {"ok": True, "generated": len(items), "items": items}
