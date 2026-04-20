from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aipayment_kb_agent.knowledge_ingestion.classifier import KnowledgeClassifier
from aipayment_kb_agent.knowledge_ingestion.deduplicator import KnowledgeDeduplicator
from aipayment_kb_agent.knowledge_ingestion.document_generator import generate_markdown
from aipayment_kb_agent.knowledge_ingestion.extractor import KnowledgeExtractor
from aipayment_kb_agent.utils.helpers import now_iso, safe_stem, sha1_text, write_json

logger = logging.getLogger(__name__)


class AutoIngestionPipeline:
    def __init__(
        self,
        auto_ingested_path: Path,
        extractor: KnowledgeExtractor,
        markdown_guidelines: str = "",
        markdown_sections: list[str] | None = None,
        markdown_section_templates: dict[str, str] | None = None,
    ):
        self.auto_ingested_path = auto_ingested_path
        self.extractor = extractor
        self.classifier = KnowledgeClassifier()
        self.deduplicator = KnowledgeDeduplicator()
        self.markdown_guidelines = markdown_guidelines
        self.markdown_sections = markdown_sections or []
        self.markdown_section_templates = markdown_section_templates or {}

    def run(
        self,
        question: str,
        answer: str,
        existing_titles: list[str],
    ) -> list[dict[str, Any]]:
        points = self.extractor.extract(question=question, answer=answer)
        outputs: list[dict[str, Any]] = []
        pending_dir = self.auto_ingested_path / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        for point in points:
            if self.deduplicator.is_duplicate(point.title, existing_titles=existing_titles):
                logger.info("auto_ingest:skip_duplicate title=%s", point.title)
                continue
            inferred_category, auto_tags = self.classifier.classify(f"{question}\n{answer}")
            category = (point.category or inferred_category or "general").strip().lower() or "general"
            markdown = generate_markdown(
                point=point,
                category=category,
                tags=auto_tags,
                source="auto_upgrade",
                question=question,
                answer=answer,
                guidelines=self.markdown_guidelines,
                required_sections=self.markdown_sections,
                section_templates=self.markdown_section_templates,
            )
            candidate_id = sha1_text(f"{point.title}|{now_iso()}")[:16]
            filename = f"{safe_stem(point.title)}_{candidate_id}.md"
            markdown_path = pending_dir / filename
            markdown_path.write_text(markdown, encoding="utf-8")

            payload = {
                "candidate_id": candidate_id,
                "question": question,
                "answer": answer,
                "title": point.title,
                "category": category,
                "tags": sorted(set(auto_tags + point.tags)),
                "markdown_path": str(markdown_path),
                "status": "pending",
                "created_at": now_iso(),
            }
            write_json(pending_dir / f"{candidate_id}.json", payload)
            outputs.append(payload)
            logger.info("auto_ingest:candidate_created id=%s", candidate_id)
        return outputs
