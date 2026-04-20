from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryState:
    query: str
    session_id: str
    auto_upgrade: bool = False
    upgrade_decision: str | None = None
