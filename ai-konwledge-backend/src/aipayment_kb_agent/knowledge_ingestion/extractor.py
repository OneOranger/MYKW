from __future__ import annotations

import json
import logging
import re
from typing import Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KnowledgePointExtract(BaseModel):
    title: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    category: str | None = None


class KnowledgeExtractor:
    def __init__(
        self,
        llm_json_call: Callable[[str], str] | None = None,
        instruction_template: str | None = None,
    ):
        self.llm_json_call = llm_json_call
        self.instruction_template = (instruction_template or "").strip()

    def _build_prompt(self, question: str, answer: str) -> str:
        if not self.instruction_template:
            return (
                "Extract 1-3 reusable knowledge points from the Q&A below.\n"
                "Return JSON array items with fields: title, summary, bullets, tags, category.\n\n"
                "Question:\n"
                f"{question}\n\n"
                "Answer:\n"
                f"{answer}\n"
            )

        prompt = self.instruction_template
        prompt = prompt.replace("{{question}}", question).replace("{{answer}}", answer)

        if "{{question}}" not in self.instruction_template and "{{answer}}" not in self.instruction_template:
            prompt = (
                f"{prompt}\n\n"
                "Question:\n"
                f"{question}\n\n"
                "Answer:\n"
                f"{answer}\n"
            )
        return prompt

    def extract(self, question: str, answer: str) -> list[KnowledgePointExtract]:
        prompt = self._build_prompt(question=question, answer=answer)
        if self.llm_json_call:
            try:
                raw = self.llm_json_call(prompt)
                items = json.loads(raw)
                return [KnowledgePointExtract.model_validate(it) for it in items]
            except RuntimeError as exc:
                logger.warning("extractor:llm_unavailable reason=%s", exc)
            except Exception:
                logger.exception("extractor:llm_parse_failed fallback_to_heuristic")

        title = question[:36] if len(question) > 36 else question
        summary = answer[:400]
        bullets = [line.strip("- ").strip() for line in answer.splitlines() if line.strip()][:5]
        tags = [tok for tok in re.split(r"[\s,，。；;、]+", question) if tok][:5]
        return [KnowledgePointExtract(title=title, summary=summary, bullets=bullets, tags=tags)]
