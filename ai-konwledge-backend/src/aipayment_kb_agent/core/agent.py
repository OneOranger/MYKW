from __future__ import annotations

import json
import logging
import math
import re
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from aipayment_kb_agent.config.settings import Settings
from aipayment_kb_agent.core.intent_router import IntentRouter, QueryIntent
from aipayment_kb_agent.core.prompt import build_answer_user_prompt, build_context_block
from aipayment_kb_agent.knowledge.auto_upgrader import AutoUpgrader
from aipayment_kb_agent.knowledge.embeddings import EmbeddingModel
from aipayment_kb_agent.knowledge.retriever import KnowledgeRetriever
from aipayment_kb_agent.knowledge.updater import KnowledgeUpdater
from aipayment_kb_agent.knowledge.vectorstore import LanceVectorStore
from aipayment_kb_agent.knowledge_ingestion.extractor import KnowledgeExtractor
from aipayment_kb_agent.knowledge_ingestion.pipeline import AutoIngestionPipeline
from aipayment_kb_agent.memory.manager import MemoryManager
from aipayment_kb_agent.models.request import QueryRequest
from aipayment_kb_agent.models.response import (
    FileMatch,
    QueryResponse,
    RetrievalMeta,
    SourceEntity,
    SourceHit,
    SourceScores,
    UpgradeDecision,
)
from aipayment_kb_agent.prompts.registry import PromptRegistry
from aipayment_kb_agent.utils.helpers import now_iso, sha1_text

logger = logging.getLogger(__name__)


class KnowledgeAgent:
    _QUESTION_HINTS = (
        "\u4ec0\u4e48",
        "\u5982\u4f55",
        "\u600e\u4e48",
        "\u4e3a\u4f55",
        "\u54ea\u4e9b",
        "\u54ea\u79cd",
        "\u54ea\u7c7b",
        "\u591a\u5c11",
        "\u51e0\u79cd",
        "\u662f\u5426",
        "\u6709\u6ca1\u6709",
        "\u6709\u65e0",
        "\u8bf7\u95ee",
        "\u5417",
        "\u5462",
        "?",
        "\uff1f",
    )

    _CN_STOPWORDS = {
        "\u4ec0\u4e48",
        "\u4ec0\u4e48\u662f",
        "\u4ec0\u4e48\u53eb",
        "\u5982\u4f55",
        "\u600e\u4e48",
        "\u4e3a\u4f55",
        "\u4e3a\u4ec0\u4e48",
        "\u8bf7\u95ee",
        "\u54ea\u4e9b",
        "\u54ea\u79cd",
        "\u54ea\u7c7b",
        "\u591a\u5c11",
        "\u51e0\u79cd",
        "\u662f\u5426",
        "\u662f\u4e0d\u662f",
        "\u6709\u65e0",
        "\u6709\u6ca1\u6709",
        "\u5417",
        "\u5462",
        "\u4e48",
        "\u7684",
        "\u4e86",
        "\u662f",
    }

    _EN_STOPWORDS = {
        "what",
        "why",
        "how",
        "which",
        "who",
        "when",
        "where",
        "is",
        "are",
        "the",
        "a",
        "an",
    }

    _FILE_QUERY_NOISE = {
        "文件",
        "文档",
        "知识库",
        "相关",
        "关于",
        "哪些",
        "有哪些",
        "列出",
        "列表",
        "清单",
        "我",
        "给我",
        "帮我",
        "展示",
        "查看",
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedder = EmbeddingModel(
            model_name=settings.embedding_model,
            local_path=settings.embedding_local_path,
            local_only=settings.embedding_local_only,
        )
        self.store = LanceVectorStore(
            db_path=settings.vector_store_path,
            table_name=settings.vector_table_name,
        )
        self.retriever = KnowledgeRetriever(embedder=self.embedder, store=self.store)
        self.updater = KnowledgeUpdater(
            raw_documents_path=settings.raw_documents_path,
            processed_documents_path=settings.processed_documents_path,
            ingestion_manifest_file=settings.ingestion_manifest_file,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            embedder=self.embedder,
            store=self.store,
        )
        self.memory = MemoryManager(
            short_file=str(settings.short_memory_file),
            long_file=str(settings.long_memory_file),
        )

        prompts_root = Path(__file__).resolve().parents[1] / "prompts"
        self.prompt_registry = PromptRegistry(prompts_root=prompts_root)
        self.intent_router = IntentRouter()
        self.client = self._build_openai_client()

        auto_upgrade_cfg = self.prompt_registry.system_prompt("auto_upgrade")
        self.auto_upgrade_instruction = str(auto_upgrade_cfg.get("system_prompt", "")).strip()

        update_guidelines_cfg = self.prompt_registry.system_prompt("update_guidelines")
        self.update_markdown_guidelines = str(update_guidelines_cfg.get("system_prompt", "")).strip()
        raw_sections = update_guidelines_cfg.get("required_sections", [])
        self.update_required_sections = [
            str(section).strip()
            for section in (raw_sections if isinstance(raw_sections, list) else [])
            if str(section).strip()
        ]
        raw_templates = update_guidelines_cfg.get("section_templates", {})
        self.update_section_templates = (
            {str(k): str(v) for k, v in raw_templates.items()}
            if isinstance(raw_templates, dict)
            else {}
        )

        extractor = KnowledgeExtractor(
            llm_json_call=self._llm_json_call,
            instruction_template=self.auto_upgrade_instruction,
        )
        pipeline = AutoIngestionPipeline(
            auto_ingested_path=settings.auto_ingested_path,
            extractor=extractor,
            markdown_guidelines=self.update_markdown_guidelines,
            markdown_sections=self.update_required_sections,
            markdown_section_templates=self.update_section_templates,
        )
        self.auto_upgrader = AutoUpgrader(
            auto_ingested_path=settings.auto_ingested_path,
            pipeline=pipeline,
            updater=self.updater,
        )

    def _build_openai_client(self) -> OpenAI | None:
        if not self.settings.openai_enabled:
            return None
        if not self.settings.openai_api_key:
            logger.warning("OpenAI disabled: API key is empty.")
            return None
        try:
            return OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )
        except Exception:
            logger.exception("OpenAI client initialization failed.")
            return None

    def _llm_json_call(self, prompt: str) -> str:
        if self.client is None:
            raise RuntimeError("OpenAI unavailable")

        resp = self.client.chat.completions.create(
            model=self.settings.model_name,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": 'Only return JSON: {"items": [...]}.'},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        payload = json.loads(content)
        items = payload.get("items", [])
        return json.dumps(items, ensure_ascii=False)

    def _llm_answer(self, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
        if self.client is None:
            return self._fallback_answer(user_prompt), 0, 0
        try:
            resp = self.client.chat.completions.create(
                model=self.settings.model_name,
                temperature=self.settings.temperature,
                max_tokens=self.settings.answer_max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = resp.choices[0].message.content or ""
            prompt_tokens = int(getattr(resp.usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(resp.usage, "completion_tokens", 0) or 0)
            return content.strip(), prompt_tokens, completion_tokens
        except Exception:
            logger.exception("LLM call failed; fallback answer used.")
            return self._fallback_answer(user_prompt), 0, 0

    @staticmethod
    def _fallback_answer(text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        key = lines[-1] if lines else "question"
        return (
            "当前模型服务暂不可用，我先给出一个通用说明：\n\n"
            f"问题：{key}\n\n"
            "建议你补充更具体的业务场景（行业、对象、约束条件），"
            "我可以据此给出更完整的分层解答和可执行方案。"
        )

    @staticmethod
    def _normalize_doc_type(value: str | None) -> str:
        key = (value or "").lower().strip()
        mapping = {
            "pdf": "pdf",
            "md": "markdown",
            "markdown": "markdown",
            "web": "web",
            "txt": "note",
            "docx": "note",
            "csv": "note",
            "xlsx": "note",
            "note": "note",
            "pptx": "slide",
            "slide": "slide",
        }
        return mapping.get(key, "note")

    @staticmethod
    def _normalize_query_text(query: str) -> str:
        return " ".join(query.strip().split())

    def _is_question_query(self, query: str) -> bool:
        q = self._normalize_query_text(query)
        return any(token in q for token in self._QUESTION_HINTS)

    def _extract_query_terms(self, query: str) -> list[str]:
        q = self._normalize_query_text(query)
        q_l = q.lower()
        terms: set[str] = set()

        for token in re.findall(r"[a-z0-9_]+", q_l):
            if len(token) < 2 or token in self._EN_STOPWORDS:
                continue
            terms.add(token)

        prefixes = (
            "\u4ec0\u4e48\u662f",
            "\u4ec0\u4e48\u53eb",
            "\u4ec0\u4e48",
            "\u8bf7\u95ee",
            "\u5982\u4f55",
            "\u600e\u4e48",
            "\u4e3a\u4f55",
            "\u4e3a\u4ec0\u4e48",
            "\u662f\u5426",
            "\u662f\u4e0d\u662f",
            "\u6709\u65e0",
            "\u6709\u6ca1\u6709",
            "\u54ea\u4e9b",
            "\u54ea\u79cd",
            "\u54ea\u7c7b",
            "\u591a\u5c11",
            "\u51e0\u79cd",
        )

        for chunk in re.findall(r"[\u4e00-\u9fff]+", q):
            unit = chunk.strip()
            for prefix in prefixes:
                if unit.startswith(prefix) and len(unit) > len(prefix):
                    unit = unit[len(prefix) :].strip()
                    break

            if len(unit) >= 2 and unit not in self._CN_STOPWORDS:
                terms.add(unit)

            if len(unit) >= 4:
                for i in range(len(unit) - 1):
                    bg = unit[i : i + 2]
                    if bg in self._CN_STOPWORDS:
                        continue
                    if any(ch in "\u4ec0\u4e48\u5982\u4f55\u600e\u4e48\u8bf7\u95ee\u662f\u5426\u5417\u5462\u54ea\u591a\u5c11\u51e0" for ch in bg):
                        continue
                    terms.add(bg)

        q_compact = q_l.replace(" ", "")
        if len(q_compact) >= 2 and q_compact not in self._CN_STOPWORDS:
            terms.add(q_compact)

        for doc_name in re.findall(r"([\u4e00-\u9fffA-Za-z0-9_\-]{2,})\s*(?:pdf|docx|pptx|xlsx|md)", q_l):
            item = doc_name.strip().lower()
            if len(item) >= 2:
                terms.add(item)

        ordered = sorted(terms, key=len, reverse=True)
        return ordered[:24]

    def _extract_file_query_targets(self, query: str) -> list[str]:
        return self.intent_router.route(query).file_targets

    def _extract_file_listing_terms(
        self,
        query: str,
        query_terms: list[str],
        intent: QueryIntent,
    ) -> list[str]:
        noise_fragments = (
            "文件",
            "文档",
            "知识库",
            "关于",
            "相关",
            "哪些",
            "有哪些",
            "我有",
            "给我",
            "帮我",
            "列出",
            "清单",
        )
        noise_chars = set("我有哪些关于的文件文档")

        terms: list[str] = []
        terms.extend(intent.topic_terms)
        terms.extend(intent.file_targets)

        cleaned: list[str] = []
        seen: set[str] = set()
        for term in terms:
            token = str(term).strip().lower()
            if len(token) < 2:
                continue
            if token in self._FILE_QUERY_NOISE:
                continue
            if any(fragment in token for fragment in noise_fragments):
                continue
            if len(token) <= 2 and all(ch in noise_chars for ch in token):
                continue
            if token.endswith("的"):
                token = token[:-1]
            token = token.strip()
            if len(token) < 2:
                continue
            if token in seen:
                continue
            seen.add(token)
            cleaned.append(token)
        return cleaned[:12]

    def _build_file_listing_candidates(
        self,
        terms: list[str],
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        rows = self.store.all_records()
        docs: dict[str, dict[str, Any]] = {}

        for row in rows:
            metadata = row.get("metadata", {})
            source_path = str(metadata.get("source", "") or "").strip()
            if not source_path:
                continue
            bucket = docs.setdefault(
                source_path,
                {
                    "title": str(metadata.get("doc_title", "") or Path(source_path).name),
                    "sourcePath": source_path,
                    "category": str(metadata.get("category", "") or "general"),
                    "docType": self._normalize_doc_type(str(metadata.get("doc_type", "") or "")),
                    "updatedAt": str(metadata.get("updated_at", "") or ""),
                    "chunks": 0,
                    "tags": set(),
                    "preview_chunks": [],
                },
            )
            bucket["chunks"] += 1
            for tag in metadata.get("tags") or []:
                text_tag = str(tag).strip()
                if text_tag:
                    bucket["tags"].add(text_tag)
            content = str(row.get("content", "") or "").strip()
            if content and len(bucket["preview_chunks"]) < 3:
                bucket["preview_chunks"].append(content)

        if not docs:
            return []

        candidates: list[dict[str, Any]] = []
        for doc in docs.values():
            tags_text = " ".join(sorted(doc["tags"]))
            preview_text = " ".join(doc["preview_chunks"])
            title = str(doc["title"])
            source_path = str(doc["sourcePath"])

            title_blob = f"{title}\n{source_path}".lower()
            evidence_blob = f"{title}\n{source_path}\n{tags_text}\n{preview_text}".lower()

            if terms:
                title_hits = [t for t in terms if t in title_blob]
                evidence_hits = [t for t in terms if t in evidence_blob]
                if not evidence_hits:
                    continue
                title_score = len(title_hits) / max(1.0, float(len(terms)))
                evidence_score = len(evidence_hits) / max(1.0, float(len(terms)))
                score = min(1.0, 0.65 * title_score + 0.35 * evidence_score + 0.25)
                highlights = evidence_hits[:8]
            else:
                score = 0.55
                highlights = []

            preview = self._trim_to_sentence(preview_text or title, max_chars=220)
            if not preview:
                preview = title

            candidates.append(
                {
                    "title": title,
                    "sourcePath": source_path,
                    "category": doc["category"],
                    "docType": doc["docType"],
                    "updatedAt": doc["updatedAt"] or now_iso(),
                    "chunks": int(doc["chunks"]),
                    "score": float(score),
                    "preview": preview,
                    "highlights": highlights,
                }
            )

        candidates.sort(
            key=lambda d: (float(d.get("score", 0.0)), int(d.get("chunks", 0))),
            reverse=True,
        )
        return candidates[:limit]

    def _build_file_listing_answer(
        self,
        query: str,
        file_matches: list[dict[str, Any]],
        terms: list[str],
    ) -> str:
        if not file_matches:
            if terms:
                term_text = "、".join(terms[:4])
                return (
                    f"我在当前知识库里没有找到与“{term_text}”直接匹配的文件。\n\n"
                    "你可以换一个关键词再试，比如：\n"
                    "1. 更具体的业务词（如“征信报告”“黑名单”“贷后”）\n"
                    "2. 文件名中的关键字（如“征信报告pdf”）\n"
                    "3. 先问“我有哪些文件”，再继续过滤。"
                )
            return (
                "当前知识库里暂时没有可列出的文件。\n\n"
                "你可以先导入文件，再执行“增量同步”后重试。"
            )

        term_text = "、".join(terms[:4]) if terms else "全部"
        lines = [
            f"我在知识库里找到了 **{len(file_matches)}** 个与“{term_text}”相关的文件：",
            "",
        ]
        for idx, item in enumerate(file_matches, start=1):
            lines.append(
                f"{idx}. {item['title']}（{item['docType']}，{item['chunks']} 个片段）"
            )
        lines.extend(
            [
                "",
                "我已经把文件做成可点击列表，你可以直接点击“在资源管理器中定位”打开本地位置。",
            ]
        )
        return "\n".join(lines)

    def _to_file_listing_hits(
        self,
        file_matches: list[dict[str, Any]],
    ) -> list[SourceHit]:
        hits: list[SourceHit] = []
        for rank, item in enumerate(file_matches, start=1):
            score = max(0.0, min(1.0, float(item.get("score", 0.0))))
            hits.append(
                SourceHit(
                    id=str(item["sourcePath"]),
                    rank=rank,
                    docTitle=str(item["title"]),
                    docType=self._normalize_doc_type(str(item["docType"])),
                    collection=str(item.get("category", "general")),
                    author=None,
                    updatedAt=str(item.get("updatedAt") or now_iso()),
                    page=None,
                    section=f"{int(item.get('chunks', 0))} chunks",
                    url=None,
                    sourcePath=str(item["sourcePath"]),
                    snippet=str(item.get("preview", "")),
                    highlights=[str(x) for x in (item.get("highlights") or [])][:8],
                    scores=SourceScores(
                        relevance=score,
                        vectorSim=score,
                        vectorDistance=max(0.0, 1.0 - score),
                        rerank=score,
                        bm25=round(score * 10, 2),
                    ),
                    summary=f"文件名与内容匹配查询意图，来源路径：{item['sourcePath']}",
                    bullets=[
                        f"文件类型：{item['docType']}",
                        f"知识分类：{item.get('category', 'general')}",
                        f"切分片段数：{int(item.get('chunks', 0))}",
                    ],
                    entities=[SourceEntity(text=str(item.get("category", "general")), type="concept")],
                    tokens=max(1, math.ceil(len(str(item.get("preview", ""))) / 4)),
                )
            )
        return hits

    def _build_file_matches_payload(self, file_matches: list[dict[str, Any]]) -> list[FileMatch]:
        payload: list[FileMatch] = []
        for item in file_matches:
            payload.append(
                FileMatch(
                    title=str(item["title"]),
                    sourcePath=str(item["sourcePath"]),
                    category=str(item.get("category", "general")),
                    docType=str(item.get("docType", "note")),
                    updatedAt=str(item.get("updatedAt", "")),
                    chunks=int(item.get("chunks", 0)),
                    score=float(item.get("score", 0.0)),
                    preview=str(item.get("preview", "")),
                )
            )
        return payload

    def _filter_retrieval_hits(
        self,
        query: str,
        raw_hits: list[dict[str, Any]],
        top_k: int,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        terms = self._extract_query_terms(query)
        query_norm = self._normalize_query_text(query).lower().replace(" ", "")
        question_like = self._is_question_query(query)
        filtered: list[dict[str, Any]] = []

        for item in raw_hits:
            record = item.get("record", {})
            content = str(record.get("content", ""))
            metadata = record.get("metadata", {})
            title = str(metadata.get("doc_title", ""))
            source = str(metadata.get("source", ""))
            search_text = f"{content}\n{title}\n{source}".lower()
            search_compact = search_text.replace(" ", "")
            sim = float(item.get("score", 0.0))

            keyword_hits = [t for t in terms if len(t) >= 2 and t.lower() in search_text][:8]
            informative_hits = [t for t in keyword_hits if len(t) >= 3]

            keyword_score = 0.0
            if terms:
                keyword_score = len(keyword_hits) / max(1.0, min(8.0, float(len(terms))))
            combined = 0.72 * sim + 0.28 * keyword_score

            exact_query_match = bool(query_norm and query_norm in search_compact)
            title_source_compact = f"{title}{source}".lower().replace(" ", "")
            title_or_source_match = bool(query_norm and query_norm in title_source_compact)

            keep = False
            if exact_query_match or title_or_source_match:
                keep = combined >= max(self.settings.retrieval_threshold, 0.33)
            elif question_like and len(query_norm) >= 4:
                # Question-like queries need stronger evidence to avoid noisy matches.
                has_multi_signal = len(keyword_hits) >= 2 and (len(informative_hits) >= 1 or sim >= 0.86)
                keep = has_multi_signal and combined >= max(self.settings.retrieval_threshold + 0.1, 0.52)
            else:
                if len(keyword_hits) >= 2:
                    keep = combined >= max(self.settings.retrieval_threshold, 0.42)
                elif len(query_norm) <= 2 and len(keyword_hits) >= 1:
                    keep = combined >= max(self.settings.retrieval_threshold, 0.34)
                elif sim >= 0.84:
                    keep = True

            if keep:
                with_extra = dict(item)
                with_extra["keyword_hits"] = keyword_hits
                with_extra["combined_score"] = combined
                filtered.append(with_extra)

        filtered.sort(
            key=lambda x: (float(x.get("combined_score", 0.0)), float(x.get("score", 0.0))),
            reverse=True,
        )
        trimmed = filtered[:top_k]
        if not trimmed:
            return [], terms

        top_score = float(trimmed[0].get("combined_score", 0.0))
        if question_like and len(query_norm) >= 4 and top_score < max(self.settings.retrieval_threshold + 0.08, 0.5):
            return [], terms
        if top_score < max(self.settings.retrieval_threshold, 0.34):
            return [], terms
        return trimmed, terms

    def _lexical_rescue_hits(
        self,
        query: str,
        query_terms: list[str],
        top_k: int,
        category: str | None,
    ) -> list[dict[str, Any]]:
        if not query_terms:
            return []

        query_norm = self._normalize_query_text(query).lower().replace(" ", "")
        question_like = self._is_question_query(query)
        has_meaningful_term = any(len(t) >= 3 for t in query_terms) or len(query_norm) <= 2
        if not has_meaningful_term:
            return []

        records = self.store.all_records()
        rescued: list[dict[str, Any]] = []

        for rec in records:
            metadata = rec.get("metadata", {})
            rec_category = str(metadata.get("category", "")).strip().lower()
            if category and rec_category != str(category).strip().lower():
                continue

            content = str(rec.get("content", ""))
            title = str(metadata.get("doc_title", ""))
            source = str(metadata.get("source", ""))
            is_auto_ingested = "_auto_ingested" in source.lower()
            search_text = f"{content}\n{title}\n{source}".lower()
            search_compact = search_text.replace(" ", "")

            keyword_hits = [t for t in query_terms if len(t) >= 2 and t.lower() in search_text][:8]
            if not keyword_hits:
                continue

            exact_query_match = bool(query_norm and query_norm in search_compact)
            long_hits = [t for t in keyword_hits if len(t) >= 3]

            if question_like and len(query_norm) >= 4 and not exact_query_match:
                if len(keyword_hits) < 2 or not long_hits:
                    continue

            if not exact_query_match and len(query_norm) > 2 and len(keyword_hits) < 2:
                if not (is_auto_ingested and len(keyword_hits) >= 1):
                    continue

            keyword_score = len(keyword_hits) / max(1.0, min(8.0, float(len(query_terms))))
            exact_boost = 0.16 if exact_query_match else 0.0
            combined = min(0.95, 0.26 + 0.62 * keyword_score + exact_boost)
            if combined < 0.58 and not exact_query_match:
                if not (is_auto_ingested and combined >= 0.45):
                    continue

            sim = max(0.0, min(0.95, combined * 0.92))
            rescued.append(
                {
                    "record": {
                        "id": rec.get("id"),
                        "content": content,
                        "metadata": metadata,
                    },
                    "score": sim,
                    "distance": max(0.0, 1.0 - sim),
                    "keyword_hits": keyword_hits,
                    "combined_score": combined,
                }
            )

        rescued.sort(
            key=lambda x: (float(x.get("combined_score", 0.0)), float(x.get("score", 0.0))),
            reverse=True,
        )
        return rescued[:top_k]

    def _auto_ingested_rescue_hits(
        self,
        query: str,
        raw_hits: list[dict[str, Any]],
        query_terms: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not raw_hits:
            return []

        query_norm = self._normalize_query_text(query).lower().replace(" ", "")
        rescued: list[dict[str, Any]] = []

        for item in raw_hits:
            record = item.get("record", {})
            metadata = record.get("metadata", {})
            source = str(metadata.get("source", "") or "").lower()
            if "_auto_ingested" not in source:
                continue

            content = str(record.get("content", ""))
            title = str(metadata.get("doc_title", ""))
            search_text = f"{content}\n{title}\n{source}".lower()
            search_compact = search_text.replace(" ", "")

            sim = max(0.0, min(1.0, float(item.get("score", 0.0))))
            keyword_hits = [t for t in query_terms if len(t) >= 2 and t.lower() in search_text][:8]
            exact_query_match = bool(query_norm and query_norm in search_compact)

            if not keyword_hits and sim < 0.6 and not exact_query_match:
                continue

            keyword_score = 0.0
            if query_terms:
                keyword_score = len(keyword_hits) / max(1.0, min(8.0, float(len(query_terms))))
            combined = 0.66 * sim + 0.34 * keyword_score
            if exact_query_match:
                combined += 0.12
            combined = max(0.0, min(0.97, combined))

            if combined < 0.58:
                continue

            with_extra = dict(item)
            with_extra["keyword_hits"] = keyword_hits
            with_extra["combined_score"] = combined
            rescued.append(with_extra)

        rescued.sort(
            key=lambda x: (float(x.get("combined_score", 0.0)), float(x.get("score", 0.0))),
            reverse=True,
        )
        return rescued[:top_k]

    def _file_target_rescue_hits(
        self,
        query: str,
        query_terms: list[str],
        top_k: int,
        category: str | None,
        file_targets: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        targets = file_targets if file_targets is not None else self._extract_file_query_targets(query)
        if not targets:
            return []

        rescued: list[dict[str, Any]] = []
        for rec in self.store.all_records():
            metadata = rec.get("metadata", {})
            rec_category = str(metadata.get("category", "")).strip().lower()
            if category and rec_category != str(category).strip().lower():
                continue

            title = str(metadata.get("doc_title", ""))
            source = str(metadata.get("source", ""))
            file_name = Path(source).name.lower() if source else ""
            title_l = title.lower()
            source_l = source.lower()

            matched_target = None
            for target in targets:
                if target in file_name or target in title_l or target in source_l:
                    matched_target = target
                    break
            if not matched_target:
                continue

            content = str(rec.get("content", ""))
            search_text = f"{content}\n{title}\n{source}".lower()
            keyword_hits = [t for t in query_terms if len(t) >= 2 and t.lower() in search_text][:8]
            keyword_score = 0.0
            if query_terms:
                keyword_score = len(keyword_hits) / max(1.0, min(8.0, float(len(query_terms))))

            combined = min(0.98, 0.72 + 0.2 * keyword_score)
            score = max(0.62, min(0.95, combined - 0.05))
            rescued.append(
                {
                    "record": {
                        "id": rec.get("id"),
                        "content": content,
                        "metadata": metadata,
                    },
                    "score": score,
                    "distance": max(0.0, 1.0 - score),
                    "keyword_hits": keyword_hits,
                    "combined_score": combined,
                }
            )

        rescued.sort(
            key=lambda x: (float(x.get("combined_score", 0.0)), float(x.get("score", 0.0))),
            reverse=True,
        )
        return rescued[:top_k]

    def _restrict_hits_to_file_targets(
        self,
        hits: list[dict[str, Any]],
        query: str,
        file_targets: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        targets = file_targets if file_targets is not None else self._extract_file_query_targets(query)
        if not targets or not hits:
            return hits

        narrowed: list[dict[str, Any]] = []
        for item in hits:
            record = item.get("record", {})
            metadata = record.get("metadata", {})
            title = str(metadata.get("doc_title", "")).lower()
            source = str(metadata.get("source", "")).lower()
            file_name = Path(source).name.lower() if source else ""
            if any(t in title or t in source or t in file_name for t in targets):
                narrowed.append(item)

        return narrowed if narrowed else hits

    def _detect_query_intent(self, query: str) -> dict[str, bool]:
        intent = self.intent_router.route(query)
        return {
            "full_doc": intent.asks_full_document,
            "report": intent.asks_report,
            "file_list": intent.asks_file_list,
        }

    def _collect_source_context(self, source_path: str, max_chunks: int = 200) -> list[dict[str, Any]]:
        if not source_path:
            return []
        rows: list[dict[str, Any]] = []
        target = str(source_path)
        for record in self.store.all_records():
            metadata = record.get("metadata", {})
            if str(metadata.get("source", "")) != target:
                continue
            rows.append(
                {
                    "record": {
                        "id": record.get("id"),
                        "content": record.get("content", ""),
                        "metadata": metadata,
                    },
                    "score": 0.92,
                    "distance": 0.08,
                    "combined_score": 0.92,
                }
            )

        rows.sort(
            key=lambda row: int(row.get("record", {}).get("metadata", {}).get("chunk_index", 0) or 0),
        )
        return rows[:max_chunks]

    @staticmethod
    def _local_answer_from_hits(question: str, hits: list[SourceHit]) -> str:
        if not hits:
            return f'No reliable KB snippets were found for "{question}".'
        lines = [f'For "{question}", the KB evidence suggests:']
        for idx, hit in enumerate(hits[:3], start=1):
            snippet = hit.snippet.replace("\n", " ").strip()
            if len(snippet) > 140:
                snippet = snippet[:140] + "..."
            lines.append(f"{idx}. {snippet} [{idx}]")
        return "\n".join(lines)
    @staticmethod
    def _trim_to_sentence(text: str, max_chars: int) -> str:
        cleaned = " ".join((text or "").split())
        if len(cleaned) <= max_chars:
            return cleaned
        cropped = cleaned[:max_chars]
        marks = list(re.finditer(r"[.!?;]", cropped))
        if marks:
            return cropped[: marks[-1].end()].strip()
        return cropped.rstrip() + "..."
    def _merge_chunk_texts(self, chunks: list[str], max_chars: int = 900) -> str:
        parts = [re.sub(r"\s+", " ", (x or "")).strip() for x in chunks if (x or "").strip()]
        if not parts:
            return ""
        merged = parts[0]
        for part in parts[1:]:
            overlap = 0
            max_overlap = min(len(merged), len(part), 240)
            for size in range(max_overlap, 23, -1):
                if merged.endswith(part[:size]):
                    overlap = size
                    break
            if overlap > 0:
                merged = f"{merged}{part[overlap:]}"
            elif part not in merged:
                merged = f"{merged}\n\n{part}"
        return self._trim_to_sentence(merged, max_chars=max_chars)
    def _extract_bullets(self, text: str, max_items: int = 3) -> list[str]:
        candidates = [x.strip() for x in re.split(r"[.!?;\n]", text or "") if x.strip()]
        return candidates[:max_items]
    def _to_source_hits(
        self,
        raw_hits: list[dict[str, Any]],
        query_terms: list[str],
        top_k: int,
    ) -> tuple[list[SourceHit], list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in raw_hits:
            record = item.get("record", {})
            metadata = record.get("metadata", {})
            source_key = str(metadata.get("source") or metadata.get("doc_title") or record.get("id") or "unknown")
            grouped.setdefault(source_key, []).append(item)
        if not grouped:
            return [], []
        group_rows: list[dict[str, Any]] = []
        for source_key, items in grouped.items():
            ordered_items = sorted(
                items,
                key=lambda row: (float(row.get("combined_score", 0.0)), float(row.get("score", 0.0))),
                reverse=True,
            )
            top_item = ordered_items[0]
            selected = ordered_items[:2]
            top_record = top_item.get("record", {})
            top_meta = top_record.get("metadata", {})
            selected_contents = [str(s.get("record", {}).get("content", "")) for s in selected]
            merged_snippet = self._merge_chunk_texts(selected_contents, max_chars=900)
            if not merged_snippet:
                merged_snippet = self._trim_to_sentence(str(top_record.get("content", "")), max_chars=900)
            highlight_terms: list[str] = []
            seen_terms: set[str] = set()
            for row in selected:
                text = str(row.get("record", {}).get("content", ""))
                for token in row.get("keyword_hits", []) or []:
                    key = str(token).strip().lower()
                    if len(key) < 2 or key in seen_terms:
                        continue
                    if key not in text.lower() and key not in merged_snippet.lower():
                        continue
                    seen_terms.add(key)
                    highlight_terms.append(str(token))
            if not highlight_terms:
                for token in query_terms:
                    key = token.lower()
                    if len(key) >= 2 and key not in seen_terms and key in merged_snippet.lower():
                        seen_terms.add(key)
                        highlight_terms.append(token)
                    if len(highlight_terms) >= 8:
                        break
            highlight_terms = highlight_terms[:8]
            chunk_indices = sorted(
                {
                    int(s.get("record", {}).get("metadata", {}).get("chunk_index", 0) or 0)
                    for s in selected
                }
            )
            if not chunk_indices:
                section_label = None
            elif len(chunk_indices) == 1:
                section_label = "1 hit snippet"
            else:
                section_label = f"{len(chunk_indices)} hit snippets"
            best_sim = max(0.0, min(1.0, float(top_item.get("score", 0.0))))
            best_combined = max(0.0, min(1.0, float(top_item.get("combined_score", best_sim))))
            group_rows.append(
                {
                    "source_key": source_key,
                    "top_item": top_item,
                    "top_meta": top_meta,
                    "selected": selected,
                    "snippet": merged_snippet,
                    "summary": self._trim_to_sentence(merged_snippet, max_chars=220),
                    "bullets": self._extract_bullets(merged_snippet, max_items=3),
                    "highlights": highlight_terms,
                    "section": section_label,
                    "sim": best_sim,
                    "combined": best_combined,
                }
            )
        group_rows.sort(key=lambda row: (row["combined"], row["sim"]), reverse=True)
        chosen_groups = group_rows[:top_k]
        output: list[SourceHit] = []
        context_hits: list[dict[str, Any]] = []
        for rank, row in enumerate(chosen_groups, start=1):
            top_meta = row["top_meta"]
            for chunk in row["selected"]:
                context_hits.append(chunk)
            output.append(
                SourceHit(
                    id=str(top_meta.get("source") or top_meta.get("doc_title") or f"source-{rank}"),
                    rank=rank,
                    docTitle=top_meta.get("doc_title", "Untitled"),
                    docType=self._normalize_doc_type(top_meta.get("doc_type")),
                    collection=top_meta.get("collection", "general"),
                    author=top_meta.get("author"),
                    updatedAt=top_meta.get("updated_at", now_iso()),
                    page=top_meta.get("page"),
                    section=row["section"],
                    url=top_meta.get("url"),
                    sourcePath=top_meta.get("source"),
                    snippet=row["snippet"],
                    highlights=row["highlights"],
                    scores=SourceScores(
                        relevance=row["combined"],
                        vectorSim=row["sim"],
                        vectorDistance=max(0.0, 1.0 - row["sim"]),
                        rerank=row["combined"],
                        bm25=round(row["combined"] * 10, 2),
                    ),
                    summary=row["summary"],
                    bullets=row["bullets"],
                    entities=[SourceEntity(text=top_meta.get("collection", "general"), type="concept")],
                    tokens=max(1, math.ceil(len(row["snippet"]) / 4)),
                )
            )
        return output, context_hits
    def _build_fallback_answer(
        self,
        question: str,
        memory_context: str,
        intent: QueryIntent | None = None,
    ) -> tuple[str, int, int]:
        base_system = self.prompt_registry.system_prompt("base").get("system_prompt", "")
        routed = intent or self.intent_router.route(question)
        style_suffix = ""
        if routed.asks_full_document:
            style_suffix = (
                "6) 用户如果要求“全文/完整内容”，要先明确当前回答来自通用知识推断而非本地文件原文，"
                "然后给出尽可能完整的结构化重构内容。\n"
            )
        elif routed.asks_report:
            style_suffix = "6) 采用正式报告格式：结论、分析、建议、下一步动作。\n"

        user_prompt = (
            "当前是知识库未命中场景，请基于通用知识进行回答。\n"
            f"用户问题：{question}\n\n"
            f"会话记忆：\n{memory_context}\n\n"
            "输出要求：\n"
            "1) 中文回答，风格自然，像 ChatGPT，不要模板化空话。\n"
            "2) 先给结论，再给解释；格式灵活，优先自然段表达，避免固定模板标题（如连续的###小节）。\n"
            "3) 增加一个简短示例/应用场景和可执行建议。\n"
            "4) 对概念型问题尽量给出充分细节（通常 400-900 中文字）。\n"
            "5) 明确说明这不是知识库命中结论，而是通用知识推断。\n"
            f"{style_suffix}"
        )
        content, prompt_tokens, completion_tokens = self._llm_answer(
            system_prompt=base_system,
            user_prompt=user_prompt,
        )
        return content.strip(), prompt_tokens, completion_tokens
    def query(self, request: QueryRequest) -> QueryResponse:
        started = time.perf_counter()
        top_k = max(1, int(request.top_k or self.settings.top_k))
        retrieval_candidate_k = max(top_k * 8, 20)
        logger.info("agent:query_start session=%s auto_upgrade=%s", request.session_id, request.auto_upgrade)

        # Auto sync raw documents before query so newly added files can be retrieved immediately.
        sync_result = self.updater.sync_raw_documents()
        if sync_result.get("changed_files", 0) > 0:
            logger.info("query pre-sync finished: %s", sync_result)

        self.memory.add_user_message(session_id=request.session_id, content=request.message)
        memory_context = self.memory.context_for_prompt(session_id=request.session_id, query=request.message)
        intent = self.intent_router.route(request.message)
        logger.info(
            "agent:intent_route session=%s mode=%s file_targets=%s",
            request.session_id,
            intent.mode,
            ",".join(intent.file_targets[:3]) if intent.file_targets else "-",
        )

        if intent.mode == "file_listing":
            listing_started = time.perf_counter()
            query_terms = self._extract_query_terms(request.message)
            listing_terms = self._extract_file_listing_terms(
                query=request.message,
                query_terms=query_terms,
                intent=intent,
            )
            candidates = self._build_file_listing_candidates(listing_terms, limit=50)
            file_matches_payload = self._build_file_matches_payload(candidates)
            hits = self._to_file_listing_hits(candidates[: max(top_k, 10)])
            content = self._build_file_listing_answer(
                query=request.message,
                file_matches=candidates,
                terms=listing_terms,
            )
            self.memory.add_assistant_message(session_id=request.session_id, content=content)
            done = time.perf_counter()
            meta = RetrievalMeta(
                totalMs=int((done - started) * 1000),
                embedMs=0,
                searchMs=int((done - listing_started) * 1000),
                rerankMs=0,
                generateMs=0,
                embedModel=self.settings.embedding_model,
                rerankModel="file-listing",
                llmModel=self.settings.model_name,
                strategy="hybrid",
                topK=top_k,
                candidatesScanned=len(candidates),
                promptTokens=0,
                completionTokens=0,
                temperature=self.settings.temperature,
                fallbackUsed=False,
            )
            message_id = sha1_text(f"{request.session_id}|{request.message}|{now_iso()}")[:16]
            response = QueryResponse(
                message_id=message_id,
                session_id=request.session_id,
                content=content,
                createdAt=now_iso(),
                hits=hits,
                meta=meta,
                citationOrder=[hit.id for hit in hits],
                upgradeDecision=None,
                canAddToKnowledge=False,
                answerMode="file_listing",
                fileMatches=file_matches_payload,
            )
            logger.info(
                "agent:query_done session=%s fallback=%s hits=%s mode=file_listing total_ms=%s",
                request.session_id,
                False,
                len(hits),
                meta.totalMs,
            )
            return response

        retrieval_hits, retrieval_timing = self.retriever.retrieve(
            query=request.message,
            top_k=retrieval_candidate_k,
            category=request.category,
        )
        filtered_hits, query_terms = self._filter_retrieval_hits(
            request.message,
            retrieval_hits,
            top_k=retrieval_candidate_k,
        )
        if filtered_hits:
            narrowed = self._restrict_hits_to_file_targets(
                filtered_hits,
                request.message,
                file_targets=intent.file_targets,
            )
            if len(narrowed) != len(filtered_hits):
                logger.info(
                    "agent:file_target_narrow session=%s before=%s after=%s",
                    request.session_id,
                    len(filtered_hits),
                    len(narrowed),
                )
            filtered_hits = narrowed
        if not filtered_hits:
            auto_hits = self._auto_ingested_rescue_hits(
                query=request.message,
                raw_hits=retrieval_hits,
                query_terms=query_terms,
                top_k=retrieval_candidate_k,
            )
            if auto_hits:
                logger.info(
                    "agent:auto_ingested_rescue session=%s hits=%s",
                    request.session_id,
                    len(auto_hits),
                )
                filtered_hits = auto_hits
                retrieval_timing["candidates"] = max(
                    int(retrieval_timing.get("candidates", 0)),
                    len(auto_hits),
                )
        if not filtered_hits:
            file_target_hits = self._file_target_rescue_hits(
                query=request.message,
                query_terms=query_terms,
                top_k=retrieval_candidate_k,
                category=request.category,
                file_targets=intent.file_targets,
            )
            if file_target_hits:
                logger.info(
                    "agent:file_target_rescue session=%s hits=%s",
                    request.session_id,
                    len(file_target_hits),
                )
                filtered_hits = file_target_hits
                retrieval_timing["candidates"] = max(
                    int(retrieval_timing.get("candidates", 0)),
                    len(file_target_hits),
                )
        if not filtered_hits:
            lexical_hits = self._lexical_rescue_hits(
                query=request.message,
                query_terms=query_terms,
                top_k=retrieval_candidate_k,
                category=request.category,
            )
            if lexical_hits:
                logger.info("agent:lexical_rescue session=%s hits=%s", request.session_id, len(lexical_hits))
                filtered_hits = lexical_hits
                retrieval_timing["candidates"] = max(
                    int(retrieval_timing.get("candidates", 0)),
                    len(lexical_hits),
                )
        fallback_used = not filtered_hits
        rerank_ms = int(retrieval_timing.get("search_ms", 0) * 0.25)

        llm_started = time.perf_counter()
        prompt_tokens = 0
        completion_tokens = 0
        can_add_to_knowledge = False
        answer_mode = intent.mode if intent.mode in {"full_document", "report"} else "knowledge_qa"
        file_matches_payload: list[FileMatch] = []

        if fallback_used:
            hits: list[SourceHit] = []
            context_hits: list[dict[str, Any]] = []
        else:
            hits, context_hits = self._to_source_hits(
                filtered_hits,
                query_terms=query_terms,
                top_k=top_k,
            )
            if not hits:
                fallback_used = True

        if fallback_used:
            content, prompt_tokens, completion_tokens = self._build_fallback_answer(
                question=request.message,
                memory_context=memory_context,
                intent=intent,
            )
            can_add_to_knowledge = True
            hits = []
        else:
            logger.info(
                "agent:grouped_hits session=%s chunk_hits=%s file_hits=%s",
                request.session_id,
                len(filtered_hits),
                len(hits),
            )
            context_candidates = context_hits if context_hits else filtered_hits
            if intent.asks_full_document and hits and hits[0].sourcePath:
                expanded_context = self._collect_source_context(hits[0].sourcePath, max_chunks=220)
                if expanded_context:
                    context_candidates = expanded_context
                    logger.info(
                        "agent:full_doc_context session=%s source=%s chunks=%s",
                        request.session_id,
                        hits[0].sourcePath,
                        len(expanded_context),
                    )

            context_block = build_context_block(context_candidates)
            retrieval_prompt = self.prompt_registry.system_prompt("knowledge_retrieval").get(
                "system_prompt", ""
            )
            if self.client is None:
                content = self._local_answer_from_hits(request.message, hits)
            else:
                user_prompt = build_answer_user_prompt(
                    question=request.message,
                    context=context_block,
                    memory_context=memory_context,
                )
                if intent.asks_full_document:
                    user_prompt += (
                        "\n\nUser intent override: The user asks for full-document style output plus summary."
                        "You must provide a document-level reconstruction from evidence with rich detail."
                        "Do not answer with only keywords."
                        "Never output retrieval jargon such as 'keywords', 'hit snippets', 'evidence basis', 'AI summary'."
                        "Output at least: (1) document outline, (2) section-by-section content summary, "
                        "(3) final executive summary."
                        "Target length should usually be >= 800 Chinese characters unless evidence is too short."
                        "If exact verbatim full text is impossible, still provide the fullest possible structured restatement."
                    )
                elif intent.asks_report:
                    user_prompt += (
                        "\n\nUser intent override: output as a formal report with sections "
                        "[Conclusion, Evidence, Analysis, Recommendations]. "
                        "Never output retrieval jargon such as 'keywords', 'hit snippets', 'evidence basis'. "
                        "Target length should usually be >= 700 Chinese characters unless evidence is short."
                    )
                content, prompt_tokens, completion_tokens = self._llm_answer(
                    system_prompt=retrieval_prompt,
                    user_prompt=user_prompt,
                )
        llm_done = time.perf_counter()

        upgrade_decision = None
        if request.auto_upgrade and can_add_to_knowledge:
            candidates = self.auto_upgrader.create_candidates(request.message, content)
            if candidates:
                upgrade_decision = UpgradeDecision(
                    enabled=True,
                    candidateId=candidates[0]["candidate_id"],
                    status="pending_review",
                    message="Knowledge candidates were extracted and moved to pending review.",
                )
            else:
                upgrade_decision = UpgradeDecision(
                    enabled=True,
                    candidateId=None,
                    status="skipped",
                    message="No new candidate was generated (likely duplicated with existing knowledge).",
                )

        self.memory.add_assistant_message(session_id=request.session_id, content=content)
        done = time.perf_counter()

        meta = RetrievalMeta(
            totalMs=int((done - started) * 1000),
            embedMs=int(retrieval_timing.get("embed_ms", 0)),
            searchMs=int(retrieval_timing.get("search_ms", 0)),
            rerankMs=rerank_ms,
            generateMs=int((llm_done - llm_started) * 1000),
            embedModel=self.settings.embedding_model,
            rerankModel="local-score-fusion",
            llmModel=self.settings.model_name,
            strategy="hybrid",
            topK=top_k,
            candidatesScanned=int(retrieval_timing.get("candidates", 0)),
            promptTokens=prompt_tokens,
            completionTokens=completion_tokens,
            temperature=self.settings.temperature,
            fallbackUsed=fallback_used,
        )

        message_id = sha1_text(f"{request.session_id}|{request.message}|{now_iso()}")[:16]
        response = QueryResponse(
            message_id=message_id,
            session_id=request.session_id,
            content=content,
            createdAt=now_iso(),
            hits=hits,
            meta=meta,
            citationOrder=[hit.id for hit in hits],
            upgradeDecision=upgrade_decision,
            canAddToKnowledge=can_add_to_knowledge,
            answerMode=answer_mode,
            fileMatches=file_matches_payload,
        )
        logger.info(
            "agent:query_done session=%s fallback=%s hits=%s total_ms=%s",
            request.session_id,
            fallback_used,
            len(hits),
            meta.totalMs,
        )
        return response

