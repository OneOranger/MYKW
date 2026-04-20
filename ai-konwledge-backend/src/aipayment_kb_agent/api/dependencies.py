from __future__ import annotations

from functools import lru_cache

from aipayment_kb_agent.config.settings import Settings, get_settings
from aipayment_kb_agent.core.agent import KnowledgeAgent


@lru_cache
def get_agent() -> KnowledgeAgent:
    settings: Settings = get_settings()
    return KnowledgeAgent(settings=settings)
