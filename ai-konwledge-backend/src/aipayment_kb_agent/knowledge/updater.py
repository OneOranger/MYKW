from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aipayment_kb_agent.knowledge.embeddings import EmbeddingModel
from aipayment_kb_agent.knowledge.loader import gather_supported_files, read_document
from aipayment_kb_agent.knowledge.splitter import split_text
from aipayment_kb_agent.knowledge.vectorstore import LanceVectorStore
from aipayment_kb_agent.utils.helpers import now_iso, read_json, safe_stem, sha1_text, write_json

logger = logging.getLogger(__name__)

DOC_TYPE_MAP = {
    "pdf": "pdf",
    "md": "markdown",
    "markdown": "markdown",
    "txt": "note",
    "docx": "note",
    "pptx": "slide",
    "csv": "note",
    "xlsx": "note",
}


@dataclass
class ParsedDocument:
    source_path: Path
    doc_type: str
    category: str
    tags: list[str]
    text: str


class KnowledgeUpdater:
    def __init__(
        self,
        raw_documents_path: Path,
        processed_documents_path: Path,
        ingestion_manifest_file: Path,
        chunk_size: int,
        chunk_overlap: int,
        embedder: EmbeddingModel,
        store: LanceVectorStore,
    ):
        self.raw_documents_path = raw_documents_path
        self.processed_documents_path = processed_documents_path
        self.ingestion_manifest_file = ingestion_manifest_file
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedder = embedder
        self.store = store

    def _file_stamp(self, path: Path) -> str:
        stat = path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"

    def _read_manifest(self) -> dict[str, dict[str, str]]:
        return read_json(self.ingestion_manifest_file, default={})

    def _write_manifest(self, payload: dict[str, dict[str, str]]) -> None:
        write_json(self.ingestion_manifest_file, payload)

    def _manifest_payload_for_files(self, files: list[Path]) -> dict[str, dict[str, str]]:
        now = now_iso()
        payload: dict[str, dict[str, str]] = {}
        for file_path in files:
            key = str(file_path.resolve())
            payload[key] = {"stamp": self._file_stamp(file_path), "updated_at": now}
        return payload

    @staticmethod
    def _split_markdown_front_matter(text: str) -> tuple[dict[str, Any], str]:
        if not text.startswith("---"):
            return {}, text
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, text
        end_idx = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_idx = idx
                break
        if end_idx is None:
            return {}, text

        front_lines = lines[1:end_idx]
        body = "\n".join(lines[end_idx + 1 :]).strip()
        metadata: dict[str, Any] = {}
        for line in front_lines:
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            key = key.strip().lower()
            value = raw_value.strip()
            if not key:
                continue
            if value.startswith("[") and value.endswith("]"):
                parsed: list[str] = []
                try:
                    literal = ast.literal_eval(value)
                    if isinstance(literal, list):
                        parsed = [str(item).strip() for item in literal if str(item).strip()]
                except (ValueError, SyntaxError):
                    raw_items = [item.strip() for item in value[1:-1].split(",")]
                    parsed = [item.strip("'\"") for item in raw_items if item]
                metadata[key] = parsed
            else:
                metadata[key] = value.strip("'\"")
        return metadata, body or text

    def sync_raw_documents(self, default_category: str = "general") -> dict[str, Any]:
        files = gather_supported_files(self.raw_documents_path)
        manifest = self._read_manifest()
        current_keys = {str(file_path.resolve()) for file_path in files}
        manifest = {k: v for k, v in manifest.items() if k in current_keys}
        changed_files: list[Path] = []
        for file_path in files:
            key = str(file_path.resolve())
            current_stamp = self._file_stamp(file_path)
            previous = manifest.get(key, {})
            if previous.get("stamp") != current_stamp:
                changed_files.append(file_path)

        if not changed_files:
            self._write_manifest(manifest)
            return {"changed_files": 0, "indexed_files": 0, "indexed_chunks": 0}

        logger.info(
            "\u68c0\u6d4b\u5230\u65b0\u589e/\u53d8\u66f4\u6587\u6863\u6570: %s\uff0c"
            "\u5f00\u59cb\u81ea\u52a8\u540c\u6b65\u5165\u5e93\u3002",
            len(changed_files),
        )
        result = self.index_files(changed_files, default_category=default_category)

        for file_path in changed_files:
            key = str(file_path.resolve())
            manifest[key] = {"stamp": self._file_stamp(file_path), "updated_at": now_iso()}
        self._write_manifest(manifest)
        return {"changed_files": len(changed_files), **result}

    def full_sync_raw_documents(self, default_category: str = "general") -> dict[str, Any]:
        files = gather_supported_files(self.raw_documents_path)
        logger.info("开始全量同步 Raw 文档...")
        logger.info("Raw 文档总数: %s", len(files))
        result = self.index_files(files, default_category=default_category)
        self._write_manifest(self._manifest_payload_for_files(files))
        return {"changed_files": len(files), **result}

    def rebuild_all_documents(self, default_category: str = "general") -> dict[str, Any]:
        raw_files = gather_supported_files(self.raw_documents_path)
        processed_files = gather_supported_files(self.processed_documents_path)

        seen: set[str] = set()
        all_files: list[Path] = []
        for file_path in [*raw_files, *processed_files]:
            key = str(file_path.resolve())
            if key in seen:
                continue
            seen.add(key)
            all_files.append(file_path)

        logger.info("开始全量重建向量索引...")
        logger.info(
            "待重建文件数: total=%s raw=%s processed=%s",
            len(all_files),
            len(raw_files),
            len(processed_files),
        )
        result = self.index_files(all_files, default_category=default_category)
        self._write_manifest(self._manifest_payload_for_files(raw_files))
        return {
            "total_files": len(all_files),
            "raw_files": len(raw_files),
            "processed_files": len(processed_files),
            **result,
        }

    def index_path(self, target: Path, default_category: str = "general") -> dict[str, Any]:
        files = gather_supported_files(target)
        return self.index_files(files, default_category=default_category)

    def index_files(self, files: list[Path], default_category: str = "general") -> dict[str, Any]:
        parsed_docs = self._load_documents(files, default_category=default_category)
        return self._index_documents(parsed_docs)

    def ingest_uploaded_file(self, file_path: Path, category: str = "general") -> dict[str, Any]:
        target = self.raw_documents_path / file_path.name
        target.write_bytes(file_path.read_bytes())
        parsed_docs = self._load_documents([target], default_category=category)
        result = self._index_documents(parsed_docs)
        return {"file": str(target), **result}

    def ingest_bytes(self, filename: str, data: bytes, category: str = "general") -> dict[str, Any]:
        target = self.raw_documents_path / filename
        target.write_bytes(data)
        parsed_docs = self._load_documents([target], default_category=category)
        result = self._index_documents(parsed_docs)
        return {"file": str(target), **result}

    def ingest_markdown(self, title: str, markdown: str, category: str, tags: list[str]) -> dict[str, Any]:
        stem = safe_stem(title)
        path = self.processed_documents_path / f"{stem}.md"
        path.write_text(markdown, encoding="utf-8")
        parsed_docs = [
            ParsedDocument(
                source_path=path,
                doc_type="markdown",
                category=category,
                tags=tags,
                text=markdown,
            )
        ]
        result = self._index_documents(parsed_docs)
        return {"file": str(path), **result}

    def stage_markdown_to_raw(
        self,
        title: str,
        markdown: str,
        *,
        filename_hint: str | None = None,
        subdir: str = "_auto_ingested",
    ) -> Path:
        target_dir = self.raw_documents_path / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        if filename_hint:
            base_name = Path(filename_hint).name
            if not base_name.lower().endswith((".md", ".markdown")):
                base_name = f"{base_name}.md"
        else:
            base_name = f"{safe_stem(title)}.md"

        target = target_dir / base_name
        if target.exists():
            target = target_dir / f"{target.stem}_{now_iso().replace(':', '').replace('-', '')}.md"
        target.write_text(markdown, encoding="utf-8")
        return target

    def _load_documents(self, files: list[Path], default_category: str) -> list[ParsedDocument]:
        logger.info("\u5f00\u59cb\u52a0\u8f7d\u6587\u6863...")
        logger.info("\u5171\u52a0\u8f7d\u6587\u6863\u6570: %s", len(files))

        parsed_docs: list[ParsedDocument] = []
        for file_path in files:
            text = read_document(file_path)
            if not text.strip():
                logger.warning("\u6587\u6863\u4e3a\u7a7a\uff0c\u8df3\u8fc7: %s", file_path.name)
                continue
            category = default_category
            tags: list[str] = []

            if file_path.suffix.lower() in {".md", ".markdown"}:
                metadata, content_body = self._split_markdown_front_matter(text)
                text = content_body
                meta_category = metadata.get("category")
                if isinstance(meta_category, str) and meta_category.strip():
                    category = meta_category.strip()
                meta_tags = metadata.get("tags")
                if isinstance(meta_tags, list):
                    tags = [str(item).strip() for item in meta_tags if str(item).strip()]

            parsed_docs.append(
                ParsedDocument(
                    source_path=file_path,
                    doc_type=DOC_TYPE_MAP.get(file_path.suffix.lower().lstrip("."), "note"),
                    category=category,
                    tags=tags,
                    text=text,
                )
            )
        return parsed_docs

    def _index_documents(self, docs: list[ParsedDocument]) -> dict[str, Any]:
        if not docs:
            return {"indexed_files": 0, "indexed_chunks": 0}

        logger.info("\u5f00\u59cb\u5207\u5206\u6587\u6863...")
        records: list[dict[str, Any]] = []
        source_count: dict[str, int] = {}
        chunk_texts: list[str] = []

        for doc in docs:
            source_abs = str(doc.source_path.resolve())
            self.store.delete_by_source(source_abs)

            chunks = split_text(
                doc.text,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
            )
            source_count[doc.source_path.name] = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                chunk_id = sha1_text(f"{source_abs}|{idx}|{chunk[:80]}")
                records.append(
                    {
                        "id": chunk_id,
                        "content": chunk,
                        "metadata": {
                            "doc_title": doc.source_path.stem,
                            "doc_type": doc.doc_type,
                            "collection": doc.category,
                            "category": doc.category,
                            "tags": doc.tags,
                            "source": source_abs,
                            "chunk_index": idx,
                            "updated_at": now_iso(),
                        },
                    }
                )
                chunk_texts.append(chunk)

        logger.info("\u5171\u5207\u5206 chunk \u6570: %s", len(records))
        logger.info("\u5207\u5206\u540e\u7684\u6587\u4ef6\u6765\u6e90\u7edf\u8ba1\uff1a")
        for name, count in source_count.items():
            logger.info("%s: %s \u4e2a chunks", name, count)

        logger.info("\u5f00\u59cb\u751f\u6210\u5411\u91cf...")
        vectors = self.embedder.embed_texts(chunk_texts)
        logger.info("\u5171\u751f\u6210\u5411\u91cf\u6570: %s", len(vectors))

        logger.info("\u5f00\u59cb\u5199\u5165 LanceDB...")
        inserted = self.store.add(records, vectors)
        total = self.store.count_rows()
        logger.info("\u5f53\u524d\u5411\u91cf\u5e93\u603b\u8bb0\u5f55\u6570: %s", total)

        return {
            "indexed_files": len(docs),
            "indexed_chunks": inserted,
            "total_chunks": total,
            "source_stats": source_count,
        }
