from __future__ import annotations

import logging
import time

from aipayment_kb_agent.knowledge.embeddings import EmbeddingModel
from aipayment_kb_agent.knowledge.vectorstore import LanceVectorStore

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    def __init__(self, embedder: EmbeddingModel, store: LanceVectorStore):
        self.embedder = embedder
        self.store = store

    def retrieve(
        self,
        query: str,
        top_k: int,
        category: str | None = None,
    ) -> tuple[list[dict], dict[str, int]]:
        t0 = time.perf_counter()
        query_vector = self.embedder.embed_query(query)
        t1 = time.perf_counter()
        filters = {"category": category} if category else None
        raw = self.store.search(query_vector, top_k=top_k, filters=filters)
        t2 = time.perf_counter()
        timings = {
            "embed_ms": int((t1 - t0) * 1000),
            "search_ms": int((t2 - t1) * 1000),
            "candidates": len(raw),
        }
        logger.info(
            "retriever:query top_k=%s category=%s hits=%s",
            top_k,
            category,
            len(raw),
        )
        return raw, timings
