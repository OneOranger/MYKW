from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from aipayment_kb_agent.api.dependencies import get_agent
from aipayment_kb_agent.core.agent import KnowledgeAgent
from aipayment_kb_agent.models.request import (
    RevealPathRequest,
    RuntimeRetrievalConfigUpdateRequest,
    UpgradeBatchReviewRequest,
    UpgradeReviewRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _is_path_within(child: Path, root: Path) -> bool:
    try:
        child.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...),
    category: str = Form(default="general"),
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    outputs = []
    for file in files:
        content = await file.read()
        outputs.append(agent.updater.ingest_bytes(filename=file.filename, data=content, category=category))
    logger.info("api:upload files=%s category=%s", len(files), category)
    return {"ok": True, "files": outputs}


@router.post("/upload-path")
def upload_path(
    local_path: str,
    category: str = "general",
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    path = Path(local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"path not found: {local_path}")
    result = agent.updater.index_path(path, default_category=category)
    return {"ok": True, **result}


@router.post("/import/sync-raw")
def sync_raw(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    result = agent.updater.sync_raw_documents()
    return {"ok": True, **result}


@router.post("/import/full-sync")
def full_sync(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    result = agent.updater.full_sync_raw_documents()
    return {"ok": True, **result}


@router.get("/documents")
def documents(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    records = agent.store.all_records()
    by_source: dict[str, dict] = {}
    for rec in records:
        md = rec.get("metadata", {})
        src = md.get("source", "")
        if not src:
            continue
        if src not in by_source:
            by_source[src] = {
                "source": src,
                "doc_title": md.get("doc_title", ""),
                "doc_type": md.get("doc_type", ""),
                "category": md.get("category", ""),
                "updated_at": md.get("updated_at", ""),
                "chunks": 0,
            }
        by_source[src]["chunks"] += 1
    return {"total_documents": len(by_source), "documents": list(by_source.values())}


@router.post("/rebuild")
def rebuild(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    result = agent.updater.rebuild_all_documents()
    return {"ok": True, "result": result}


@router.get("/vectorstore/stats")
def vectorstore_stats(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    return {
        "ok": True,
        "db_path": str(agent.settings.vector_store_path),
        "table_name": agent.settings.vector_table_name,
        "total_rows": agent.store.count_rows(),
    }


@router.get("/runtime/retrieval-config")
def get_runtime_retrieval_config(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    return {
        "ok": True,
        "top_k": int(agent.settings.top_k),
    }


@router.post("/runtime/retrieval-config")
def set_runtime_retrieval_config(
    payload: RuntimeRetrievalConfigUpdateRequest,
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    if payload.top_k is not None:
        agent.settings.top_k = int(payload.top_k)
    return {
        "ok": True,
        "top_k": int(agent.settings.top_k),
    }


@router.post("/vectorstore/recreate")
def vectorstore_recreate(agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    # MiniLM-L6-v2 embedding dim = 384
    agent.store.recreate_table(vector_dim=384)
    rebuild_result = agent.updater.rebuild_all_documents()
    return {
        "ok": True,
        "message": "vector table recreated and full rebuild finished",
        "table_name": agent.settings.vector_table_name,
        "total_rows": agent.store.count_rows(),
        "rebuild": rebuild_result,
    }


@router.get("/upgrade/pending")
def upgrade_pending(
    category: str | None = Query(default=None),
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    items = agent.auto_upgrader.list_pending()
    if category:
        wanted = category.strip().lower()
        items = [item for item in items if str(item.get("category", "")).strip().lower() == wanted]
    return {"ok": True, "total": len(items), "items": items}


@router.get("/upgrade/pending/{candidate_id}/preview")
def upgrade_preview(candidate_id: str, agent: KnowledgeAgent = Depends(get_agent)) -> dict:
    try:
        return {"ok": True, **agent.auto_upgrader.preview_pending_markdown(candidate_id)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/upgrade/review/batch")
def upgrade_review_batch(
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


@router.post("/upgrade/review/{candidate_id}")
def upgrade_review(
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


@router.post("/files/reveal")
def reveal_in_explorer(
    payload: RevealPathRequest,
    agent: KnowledgeAgent = Depends(get_agent),
) -> dict:
    target = Path(payload.path).expanduser().resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"path not found: {target}")

    data_root = agent.settings.data_path.resolve()
    if not _is_path_within(target, data_root):
        raise HTTPException(status_code=403, detail="path is outside allowed data directory")

    cmd = ["explorer", str(target)] if target.is_dir() else ["explorer", f"/select,{target}"]
    subprocess.Popen(cmd)
    return {"ok": True, "path": str(target)}
