from __future__ import annotations


def split_text(text: str, chunk_size: int = 600, overlap: int = 120) -> list[str]:
    cleaned = " ".join(text.replace("\r", "\n").split())
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks
