from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aipayment_kb_agent.utils.helpers import now_iso, read_json, write_json


@dataclass
class LongTermMemory:
    file_path: str
    _items: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._items = read_json(self.path_obj, default=[])

    @property
    def path_obj(self):
        from pathlib import Path

        return Path(self.file_path)

    def add_fact(self, session_id: str, summary: str, tags: list[str] | None = None) -> None:
        self._items.append(
            {
                "session_id": session_id,
                "summary": summary,
                "tags": tags or [],
                "created_at": now_iso(),
            }
        )
        self.persist()

    def all(self) -> list[dict[str, Any]]:
        return self._items

    def persist(self) -> None:
        write_json(self.path_obj, self._items)
