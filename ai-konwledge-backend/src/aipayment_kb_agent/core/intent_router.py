from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class QueryIntent:
    mode: str
    asks_full_document: bool
    asks_report: bool
    asks_summary: bool
    asks_file_list: bool
    file_targets: list[str] = field(default_factory=list)
    topic_terms: list[str] = field(default_factory=list)


class IntentRouter:
    _FULL_DOC_HINTS = (
        "\u5168\u90e8\u5185\u5bb9",
        "\u5168\u6587",
        "\u5b8c\u6574\u5185\u5bb9",
        "\u5b8c\u6574\u7248\u672c",
        "\u539f\u6587",
        "\u9010\u6bb5",
        "\u8be6\u7ec6\u5c55\u5f00",
        "\u5b8c\u6574\u8f93\u51fa",
        "\u5168\u91cf\u5185\u5bb9",
    )

    _REPORT_HINTS = (
        "\u62a5\u544a",
        "\u603b\u7ed3",
        "\u6574\u7406",
        "\u5206\u6790",
        "\u63d0\u7eb2",
        "\u7ed3\u8bba",
        "\u8f93\u51fa\u65b9\u6848",
        "\u5f62\u6210\u6587\u6863",
        "\u7ed9\u51fa\u65b9\u6848",
    )

    _SUMMARY_HINTS = (
        "\u603b\u7ed3",
        "\u63d0\u70bc",
        "\u6982\u62ec",
        "\u5f52\u7eb3",
    )

    _FILE_LIST_ACTION_HINTS = (
        "\u6709\u54ea\u4e9b",
        "\u54ea\u4e9b",
        "\u5217\u51fa",
        "\u5217\u8868",
        "\u6e05\u5355",
        "\u5e2e\u6211\u627e",
        "\u7ed9\u6211\u627e",
        "\u7ed9\u6211\u770b",
        "\u5c55\u793a",
        "\u67e5\u770b",
    )

    _FILE_EXT_HINTS = ("pdf", "docx", "pptx", "xlsx", "md", "txt")

    _TOPIC_STOPWORDS = {
        "\u6211",
        "\u6709\u54ea\u4e9b",
        "\u54ea\u4e9b",
        "\u5173\u4e8e",
        "\u76f8\u5173",
        "\u6587\u4ef6",
        "\u6587\u6863",
        "\u77e5\u8bc6\u5e93",
        "\u91cc\u9762",
        "\u91cc",
        "\u6240\u6709",
        "\u5168\u90e8",
        "\u4e00\u4e0b",
        "\u5e2e\u6211",
        "\u7ed9\u6211",
        "\u663e\u793a",
        "\u5217\u51fa",
        "\u67e5\u627e",
        "\u7684",
    }

    @staticmethod
    def _normalize_topic_token(token: str) -> str:
        value = str(token or "").strip().lower()
        if not value:
            return ""

        for prefix in (
            "\u5173\u4e8e",
            "\u6709\u5173",
            "\u76f8\u5173",
            "\u5305\u542b",
            "\u5305\u62ec",
        ):
            if value.startswith(prefix) and len(value) > len(prefix):
                value = value[len(prefix) :]
                break

        for suffix in (
            "\u7684",
            "\u6587\u4ef6",
            "\u6587\u6863",
            "\u8d44\u6599",
        ):
            if value.endswith(suffix) and len(value) > len(suffix):
                value = value[: -len(suffix)]
                break

        return value.strip("-_ ")

    @staticmethod
    def _normalize_query_text(query: str) -> str:
        return " ".join((query or "").strip().split())

    def _extract_file_targets(self, query: str) -> list[str]:
        q = self._normalize_query_text(query).lower()
        targets: set[str] = set()
        ext_group = "|".join(self._FILE_EXT_HINTS)
        pattern = rf"([\u4e00-\u9fffA-Za-z0-9_\-]{{2,}})\s*(?:[.。]?\s*)({ext_group})"
        for item, ext in re.findall(pattern, q):
            stem = item.strip().lower()
            if len(stem) < 2:
                continue
            targets.add(stem)
            targets.add(f"{stem}.{ext}")
            targets.add(f"{stem}{ext}")
        return sorted(targets, key=len, reverse=True)[:10]

    def _extract_topic_terms(self, query: str) -> list[str]:
        q = self._normalize_query_text(query)
        q_l = q.lower()
        terms: list[str] = []

        patterns = (
            r"\u5173\u4e8e([\u4e00-\u9fffA-Za-z0-9_\-]{1,20})(?:\u7684)?(?:\u6587\u4ef6|\u6587\u6863)",
            r"\u5305\u542b([\u4e00-\u9fffA-Za-z0-9_\-]{1,20})(?:\u7684)?(?:\u6587\u4ef6|\u6587\u6863)",
            r"([\u4e00-\u9fffA-Za-z0-9_\-]{1,20})(?:\u76f8\u5173)?(?:\u6587\u4ef6|\u6587\u6863)\u6709\u54ea\u4e9b",
            r"\u6211\u6709\u54ea\u4e9b([\u4e00-\u9fffA-Za-z0-9_\-]{1,20})(?:\u76f8\u5173)?(?:\u6587\u4ef6|\u6587\u6863)",
        )
        for pat in patterns:
            for match in re.findall(pat, q):
                token = self._normalize_topic_token(str(match))
                if token and token not in self._TOPIC_STOPWORDS:
                    terms.append(token)

        for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", q):
            piece = chunk.strip()
            if not piece:
                continue
            for stop in self._TOPIC_STOPWORDS:
                piece = piece.replace(stop, "")
            piece = piece.strip()
            if len(piece) >= 2:
                terms.append(self._normalize_topic_token(piece.lower()))

        for token in re.findall(r"[a-z0-9_]{2,}", q_l):
            normalized = self._normalize_topic_token(token)
            if normalized and normalized not in self._TOPIC_STOPWORDS:
                terms.append(normalized)

        deduped: list[str] = []
        seen: set[str] = set()
        for term in terms:
            t = term.strip()
            if len(t) < 2:
                continue
            if t in seen:
                continue
            seen.add(t)
            deduped.append(t)
        return deduped[:10]

    def route(self, query: str) -> QueryIntent:
        q = self._normalize_query_text(query).lower()
        asks_full_document = any(token in q for token in self._FULL_DOC_HINTS)
        asks_report = any(token in q for token in self._REPORT_HINTS)
        asks_summary = any(token in q for token in self._SUMMARY_HINTS)
        file_targets = self._extract_file_targets(query=q)
        topic_terms = self._extract_topic_terms(query=q)

        asks_file_entity = ("\u6587\u4ef6" in q) or ("\u6587\u6863" in q)
        asks_file_action = any(token in q for token in self._FILE_LIST_ACTION_HINTS)
        asks_file_list = asks_file_entity and asks_file_action and not asks_full_document

        if asks_file_list:
            mode = "file_listing"
        elif asks_full_document:
            mode = "full_document"
        elif asks_report:
            mode = "report"
        else:
            mode = "knowledge_qa"

        return QueryIntent(
            mode=mode,
            asks_full_document=asks_full_document,
            asks_report=asks_report,
            asks_summary=asks_summary,
            asks_file_list=asks_file_list,
            file_targets=file_targets,
            topic_terms=topic_terms,
        )
