from __future__ import annotations

from typing import Any


def build_context_block(hits: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        record = hit.get("record", {})
        metadata = record.get("metadata", {})
        content = str(record.get("content", "")).strip()
        title = str(metadata.get("doc_title", "untitled"))
        source = str(metadata.get("source", ""))
        chunk_index = metadata.get("chunk_index")
        lines.append(
            f"[{idx}] title={title} | source={source} | chunk={chunk_index}\n"
            f"content:\n{content}\n"
        )
    return "\n".join(lines)


def build_answer_user_prompt(question: str, context: str, memory_context: str) -> str:
    return (
        "You are answering with local knowledge-base evidence.\n\n"
        f"User question:\n{question}\n\n"
        f"Conversation memory:\n{memory_context}\n\n"
        f"Retrieved evidence:\n{context}\n\n"
        "Answer requirements:\n"
        "1) Provide a clear conclusion first, then structured explanation.\n"
        "2) Keep the answer natural and vivid like ChatGPT, not rigid or formulaic.\n"
        "3) Add citations [n] for key factual statements.\n"
        "4) Do not invent facts outside the evidence; if insufficient, say what is missing.\n"
        "5) Reply in Chinese unless user explicitly asks another language.\n"
        "6) Prefer natural paragraphs; use short headings only when helpful.\n"
    )
