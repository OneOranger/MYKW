from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import lancedb
import numpy as np
import pyarrow as pa

logger = logging.getLogger(__name__)


class LanceVectorStore:
    def __init__(self, db_path: Path, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.db_path))
        self._table = None
        self._vector_dim: int | None = None
        self._load_existing_table()

    def _load_existing_table(self) -> None:
        list_result = self.db.list_tables()
        if isinstance(list_result, list):
            table_names = list_result
        else:
            table_names = list(getattr(list_result, "tables", []) or [])
        if self.table_name in table_names:
            self._table = self.db.open_table(self.table_name)
            schema = self._table.schema
            vector_field = schema.field("vector")
            if pa.types.is_fixed_size_list(vector_field.type):
                self._vector_dim = vector_field.type.list_size
            logger.info(
                "LanceDB 表已加载: %s, 当前记录数: %s",
                self.table_name,
                self.count_rows(),
            )

    def _build_schema(self, vector_dim: int) -> pa.Schema:
        return pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), vector_dim)),
                pa.field("content", pa.string()),
                pa.field("doc_title", pa.string()),
                pa.field("doc_type", pa.string()),
                pa.field("collection", pa.string()),
                pa.field("category", pa.string()),
                pa.field("tags", pa.list_(pa.string())),
                pa.field("source", pa.string()),
                pa.field("chunk_index", pa.int32()),
                pa.field("updated_at", pa.string()),
            ]
        )

    def ensure_table(self, vector_dim: int) -> None:
        if self._table is not None:
            return
        schema = self._build_schema(vector_dim=vector_dim)
        self._table = self.db.create_table(self.table_name, schema=schema, mode="overwrite")
        self._vector_dim = vector_dim
        logger.info("LanceDB 表已创建: %s", self.table_name)

    def recreate_table(self, vector_dim: int = 384) -> None:
        schema = self._build_schema(vector_dim=vector_dim)
        self._table = self.db.create_table(self.table_name, schema=schema, mode="overwrite")
        self._vector_dim = vector_dim
        logger.info("LanceDB 表已重建: %s (dim=%s)", self.table_name, vector_dim)

    @property
    def table(self):
        if self._table is None:
            raise RuntimeError("LanceDB table not initialized")
        return self._table

    def add(self, records: list[dict[str, Any]], vectors: np.ndarray) -> int:
        if len(records) == 0:
            return 0
        if len(records) != len(vectors):
            raise ValueError("records and vectors length mismatch")
        if vectors.ndim != 2:
            raise ValueError("vectors must be 2D array")

        vector_dim = int(vectors.shape[1])
        self.ensure_table(vector_dim=vector_dim)
        if self._vector_dim is not None and self._vector_dim != vector_dim:
            raise ValueError(
                f"vector dim mismatch: table={self._vector_dim}, incoming={vector_dim}"
            )

        rows = []
        for rec, vec in zip(records, vectors, strict=True):
            metadata = rec.get("metadata", {})
            rows.append(
                {
                    "id": rec.get("id"),
                    "vector": [float(x) for x in vec.tolist()],
                    "content": rec.get("content", ""),
                    "doc_title": metadata.get("doc_title", ""),
                    "doc_type": metadata.get("doc_type", ""),
                    "collection": metadata.get("collection", ""),
                    "category": metadata.get("category", ""),
                    "tags": metadata.get("tags", []) or [],
                    "source": metadata.get("source", ""),
                    "chunk_index": int(metadata.get("chunk_index", 0)),
                    "updated_at": metadata.get("updated_at", ""),
                }
            )

        ids = [row["id"] for row in rows if row["id"]]
        if ids:
            self.delete_by_ids(ids)
        self.table.add(rows)
        logger.info("已新增写入 %s 条记录到表: %s", len(rows), self.table_name)
        return len(rows)

    def delete_by_source(self, source: str) -> None:
        if self._table is None:
            return
        escaped = source.replace("'", "''")
        self.table.delete(f"source = '{escaped}'")

    def delete_by_ids(self, ids: list[str]) -> None:
        if self._table is None or not ids:
            return
        escaped_ids = []
        for item in ids:
            escaped = item.replace("'", "''")
            escaped_ids.append(f"'{escaped}'")
        for i in range(0, len(escaped_ids), 300):
            part = ",".join(escaped_ids[i : i + 300])
            self.table.delete(f"id IN ({part})")

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        if self._table is None:
            return []
        if query_vector.ndim != 1:
            raise ValueError("query_vector must be 1D array")

        query = self.table.search([float(x) for x in query_vector.tolist()])
        if filters:
            clauses = []
            for key, val in filters.items():
                escaped = str(val).replace("'", "''")
                clauses.append(f"{key} = '{escaped}'")
            if clauses:
                query = query.where(" AND ".join(clauses))
        rows = query.limit(top_k).to_list()
        results: list[dict[str, Any]] = []
        for row in rows:
            distance = float(row.get("_distance", 1.0))
            similarity = 1.0 / (1.0 + max(0.0, distance))
            record = {
                "id": row.get("id"),
                "content": row.get("content", ""),
                "metadata": {
                    "doc_title": row.get("doc_title"),
                    "doc_type": row.get("doc_type"),
                    "collection": row.get("collection"),
                    "category": row.get("category"),
                    "tags": row.get("tags") or [],
                    "source": row.get("source"),
                    "chunk_index": row.get("chunk_index"),
                    "updated_at": row.get("updated_at"),
                },
            }
            results.append({"record": record, "score": similarity, "distance": distance})
        return results

    def all_records(self) -> list[dict[str, Any]]:
        if self._table is None:
            return []
        rows = self.table.to_arrow().to_pylist()
        output: list[dict[str, Any]] = []
        for row in rows:
            output.append(
                {
                    "id": row.get("id"),
                    "content": row.get("content", ""),
                    "metadata": {
                        "doc_title": row.get("doc_title"),
                        "doc_type": row.get("doc_type"),
                        "collection": row.get("collection"),
                        "category": row.get("category"),
                        "tags": row.get("tags") or [],
                        "source": row.get("source"),
                        "chunk_index": row.get("chunk_index"),
                        "updated_at": row.get("updated_at"),
                    },
                }
            )
        return output

    def count_rows(self) -> int:
        if self._table is None:
            return 0
        return int(self.table.count_rows())
