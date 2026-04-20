from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from aipayment_kb_agent.utils.helpers import read_json, write_json


@dataclass
class ShortTermMemory:
    file_path: str
    window_size: int = 20
    _store: dict[str, deque[dict[str, Any]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        raw = read_json(path=self.path_obj, default={})
        for session_id, messages in raw.items():
            self._store[session_id] = deque(messages, maxlen=self.window_size)

    @property
    def path_obj(self):
        from pathlib import Path

        return Path(self.file_path)

    def add(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = deque(maxlen=self.window_size)
        self._store[session_id].append({"role": role, "content": content})
        self.persist()

    def get(self, session_id: str) -> list[dict[str, Any]]:
        return list(self._store.get(session_id, []))

    def persist(self) -> None:
        payload = {k: list(v) for k, v in self._store.items()}
        write_json(self.path_obj, payload)
