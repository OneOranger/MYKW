from __future__ import annotations


class MemoryRetriever:
    def __init__(self, long_term_items: list[dict]):
        self.long_term_items = long_term_items

    def search(self, query: str, limit: int = 3) -> list[dict]:
        query_l = query.lower()
        scored = []
        for item in self.long_term_items:
            summary = item.get("summary", "")
            score = sum(1 for tok in query_l.split() if tok and tok in summary.lower())
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]
