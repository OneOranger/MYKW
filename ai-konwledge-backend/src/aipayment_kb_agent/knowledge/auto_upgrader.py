from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aipayment_kb_agent.knowledge.updater import KnowledgeUpdater
from aipayment_kb_agent.knowledge_ingestion.pipeline import AutoIngestionPipeline
from aipayment_kb_agent.utils.helpers import now_iso, read_json, write_json

logger = logging.getLogger(__name__)


class AutoUpgrader:
    def __init__(self, auto_ingested_path: Path, pipeline: AutoIngestionPipeline, updater: KnowledgeUpdater):
        self.auto_ingested_path = auto_ingested_path
        self.pipeline = pipeline
        self.updater = updater

    @property
    def pending_dir(self) -> Path:
        return self.auto_ingested_path / "pending"

    @property
    def reviewed_dir(self) -> Path:
        return self.auto_ingested_path / "reviewed"

    def create_candidates(self, question: str, answer: str) -> list[dict[str, Any]]:
        existing_titles = [
            rec.get("metadata", {}).get("doc_title", "")
            for rec in self.updater.store.all_records()
        ]
        return self.pipeline.run(question=question, answer=answer, existing_titles=existing_titles)

    def list_pending(self) -> list[dict[str, Any]]:
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        items = []
        for path in sorted(self.pending_dir.glob("*.json")):
            items.append(read_json(path, default={}))
        return items

    def get_pending(self, candidate_id: str) -> dict[str, Any]:
        path = self.pending_dir / f"{candidate_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"candidate not found: {candidate_id}")
        return read_json(path, default={})

    def preview_pending_markdown(self, candidate_id: str) -> dict[str, Any]:
        payload = self.get_pending(candidate_id)
        markdown_path = Path(payload.get("markdown_path", ""))
        if not markdown_path.exists():
            raise FileNotFoundError(f"markdown not found for candidate: {candidate_id}")
        markdown = markdown_path.read_text(encoding="utf-8")
        return {"item": payload, "markdown": markdown}

    def review(self, candidate_id: str, action: str, reviewer: str, note: str | None = None) -> dict[str, Any]:
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.reviewed_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.pending_dir / f"{candidate_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"candidate not found: {candidate_id}")
        payload = read_json(json_path, default={})
        payload["status"] = "approved" if action == "approve" else "rejected"
        payload["reviewer"] = reviewer
        payload["review_note"] = note
        payload["reviewed_at"] = now_iso()

        if action == "approve":
            md_path = Path(payload["markdown_path"])
            markdown = md_path.read_text(encoding="utf-8")
            staged_path = self.updater.stage_markdown_to_raw(
                title=payload["title"],
                markdown=markdown,
                filename_hint=md_path.name,
            )
            payload["raw_path"] = str(staged_path)
            payload["vector_status"] = "pending_sync"
            payload["vector_message"] = "Approved and staged to raw documents. Please run incremental sync."
        reviewed_json = self.reviewed_dir / f"{candidate_id}.json"
        write_json(reviewed_json, payload)
        json_path.unlink(missing_ok=True)
        md_path = Path(payload["markdown_path"])
        reviewed_md = self.reviewed_dir / md_path.name
        if md_path.exists():
            reviewed_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
            md_path.unlink(missing_ok=True)
        logger.info("auto_upgrade:review id=%s action=%s", candidate_id, action)
        return payload
