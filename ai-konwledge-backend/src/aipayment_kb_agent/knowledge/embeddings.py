from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModel:
    _MODEL_CACHE: dict[str, SentenceTransformer] = {}

    def __init__(self, model_name: str, local_path: str = "", local_only: bool = True):
        self.model_name = model_name
        self.local_path = local_path.strip()
        self.local_only = local_only
        self._model: SentenceTransformer | None = None

    def _resolve_cached_snapshot(self) -> Path | None:
        cache_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
        model_key = self.model_name.replace("/", "--")
        model_dir = cache_home / "hub" / f"models--{model_key}"
        if not model_dir.exists():
            return None

        ref_main = model_dir / "refs" / "main"
        if ref_main.exists():
            revision = ref_main.read_text(encoding="utf-8").strip()
            snapshot = model_dir / "snapshots" / revision
            if snapshot.exists():
                return snapshot

        snapshots_dir = model_dir / "snapshots"
        if snapshots_dir.exists():
            snapshots = [p for p in snapshots_dir.iterdir() if p.is_dir()]
            if snapshots:
                snapshots.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return snapshots[0]
        return None

    def _resolve_model_source(self) -> str:
        if self.local_path:
            custom = Path(self.local_path).expanduser().resolve()
            if not custom.exists():
                raise RuntimeError(f"EMBEDDING_LOCAL_PATH does not exist: {custom}")
            return str(custom)

        if self.local_only:
            cached = self._resolve_cached_snapshot()
            if cached is None:
                raise RuntimeError(
                    "Embedding model not found in local cache. "
                    "Please set EMBEDDING_LOCAL_PATH or pre-download the model."
                )
            return str(cached)

        return self.model_name

    @property
    def model(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model

        source = self._resolve_model_source()
        cache_key = f"{source}|local_only={self.local_only}"
        cached_model = self._MODEL_CACHE.get(cache_key)
        if cached_model is not None:
            self._model = cached_model
            return self._model

        if self.local_only:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        logger.info(
            "embedding:model_load name=%s source=%s local_only=%s",
            self.model_name,
            source,
            self.local_only,
        )
        self._model = SentenceTransformer(
            source,
            local_files_only=self.local_only,
        )
        self._MODEL_CACHE[cache_key] = self._model
        return self._model

    def warmup(self) -> None:
        _ = self.model

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        vectors = self.embed_texts([text])
        return vectors[0]
