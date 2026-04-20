from __future__ import annotations

from difflib import SequenceMatcher


class KnowledgeDeduplicator:
    def is_duplicate(self, title: str, existing_titles: list[str], threshold: float = 0.88) -> bool:
        target = title.strip().lower()
        if not target:
            return False
        for item in existing_titles:
            ratio = SequenceMatcher(a=target, b=item.strip().lower()).ratio()
            if ratio >= threshold:
                return True
        return False
