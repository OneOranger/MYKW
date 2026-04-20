from __future__ import annotations

from aipayment_kb_agent.knowledge_ingestion.extractor import KnowledgePointExtract
from aipayment_kb_agent.utils.helpers import now_iso


def _normalize_sections(required_sections: list[str] | None) -> list[str]:
    defaults = ["Summary", "Original Question", "Original Answer Snapshot", "Key Points"]
    if not required_sections:
        return defaults
    normalized: list[str] = []
    for section in required_sections:
        name = str(section).strip()
        if not name:
            continue
        normalized.append(name)
    return normalized or defaults


def _section_text(
    section_name: str,
    *,
    point: KnowledgePointExtract,
    question_block: str,
    answer_block: str,
    bullets_text: str,
    section_templates: dict[str, str],
) -> str:
    lower_name = section_name.lower()
    if lower_name == "summary":
        return point.summary.strip() or "-"
    if lower_name == "original question":
        return question_block
    if lower_name == "original answer snapshot":
        return answer_block
    if lower_name == "key points":
        return bullets_text or "- None"

    template = section_templates.get(section_name, "").strip()
    if template:
        return template
    return "-"


def generate_markdown(
    point: KnowledgePointExtract,
    category: str,
    tags: list[str],
    source: str,
    *,
    question: str | None = None,
    answer: str | None = None,
    guidelines: str = "",
    required_sections: list[str] | None = None,
    section_templates: dict[str, str] | None = None,
) -> str:
    all_tags = sorted(set(tags + point.tags))
    tags_text = ", ".join(all_tags)
    bullets_text = "\n".join(f"- {item}" for item in point.bullets if str(item).strip())

    answer_excerpt = (answer or "").strip()
    if len(answer_excerpt) > 2200:
        answer_excerpt = answer_excerpt[:2200] + "\n\n... (truncated)"

    question_block = (question or "").strip() or "-"
    answer_block = answer_excerpt or "-"
    normalized_sections = _normalize_sections(required_sections)
    templates = section_templates or {}

    body_parts: list[str] = []
    for section_name in normalized_sections:
        section_value = _section_text(
            section_name,
            point=point,
            question_block=question_block,
            answer_block=answer_block,
            bullets_text=bullets_text,
            section_templates=templates,
        )
        body_parts.append(f"## {section_name}\n{section_value}\n")

    guidelines_note = ""
    if guidelines.strip():
        guidelines_note = (
            "\n<!-- generation_guidelines_applied: update_guidelines.yaml -->\n"
        )

    return (
        "---\n"
        f'title: "{point.title}"\n'
        f"category: {category}\n"
        f"tags: [{tags_text}]\n"
        f"source: {source}\n"
        f"created_at: {now_iso()}\n"
        "---\n\n"
        + "\n".join(body_parts)
        + guidelines_note
    )
