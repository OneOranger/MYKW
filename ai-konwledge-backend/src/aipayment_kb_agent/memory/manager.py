from __future__ import annotations

import logging

from aipayment_kb_agent.memory.compressor import compress_messages
from aipayment_kb_agent.memory.long_term import LongTermMemory
from aipayment_kb_agent.memory.retriever import MemoryRetriever
from aipayment_kb_agent.memory.short_term import ShortTermMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, short_file: str, long_file: str):
        self.short_term = ShortTermMemory(file_path=short_file)
        self.long_term = LongTermMemory(file_path=long_file)

    def add_user_message(self, session_id: str, content: str) -> None:
        logger.info("short_term:add role=user session=%s", session_id)
        self.short_term.add(session_id=session_id, role="user", content=content)

    def add_assistant_message(self, session_id: str, content: str) -> None:
        logger.info("short_term:add role=assistant session=%s", session_id)
        self.short_term.add(session_id=session_id, role="assistant", content=content)
        compact = content[:240]
        self.long_term.add_fact(session_id=session_id, summary=compact)
        logger.info("long_term:add session=%s", session_id)

    def context_for_prompt(self, session_id: str, query: str) -> str:
        short_messages = self.short_term.get(session_id)
        short_block = compress_messages(short_messages)
        retriever = MemoryRetriever(self.long_term.all())
        long_hits = retriever.search(query=query)
        long_block = "\n".join(f"- {it['summary']}" for it in long_hits)
        return f"[短期记忆]\n{short_block}\n\n[长期记忆命中]\n{long_block}".strip()
