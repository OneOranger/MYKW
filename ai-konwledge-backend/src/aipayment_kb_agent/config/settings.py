from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_name: str = "AI Knowledge Backend"
    api_prefix: str = "/api/v1"
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    openai_enabled: bool = Field(default=True, alias="OPENAI_ENABLED")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.gptsapi.net/v1", alias="OPENAI_BASE_URL")
    model_name: str = Field(default="gpt-4o-mini", alias="MODEL_NAME")
    temperature: float = Field(default=0.3, alias="TEMPERATURE")
    answer_max_tokens: int = Field(default=1800, alias="ANSWER_MAX_TOKENS")

    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_local_path: str = Field(default="", alias="EMBEDDING_LOCAL_PATH")
    embedding_local_only: bool = Field(default=True, alias="EMBEDDING_LOCAL_ONLY")

    top_k: int = Field(default=5, alias="TOP_K")
    retrieval_threshold: float = Field(default=0.35, alias="RETRIEVAL_THRESHOLD")
    web_fallback_enabled: bool = Field(default=False, alias="WEB_FALLBACK_ENABLED")
    chunk_size: int = Field(default=100, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=20, alias="CHUNK_OVERLAP")

    data_dir: str = Field(default="data", alias="DATA_DIR")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    vector_table_name: str = Field(default="knowledge_chunks", alias="VECTOR_TABLE_NAME")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def data_path(self) -> Path:
        return self.project_root / self.data_dir

    @property
    def log_path(self) -> Path:
        return self.project_root / self.log_dir

    @property
    def raw_documents_path(self) -> Path:
        return self.data_path / "documents" / "raw"

    @property
    def processed_documents_path(self) -> Path:
        return self.data_path / "documents" / "processed"

    @property
    def auto_ingested_path(self) -> Path:
        return self.data_path / "documents" / "auto_ingested"

    @property
    def vector_store_path(self) -> Path:
        return self.data_path / "vectorstores"

    @property
    def ingestion_manifest_file(self) -> Path:
        return self.vector_store_path / "ingestion_manifest.json"

    @property
    def short_memory_file(self) -> Path:
        return self.data_path / "short_memory.json"

    @property
    def long_memory_file(self) -> Path:
        return self.data_path / "long_memory.json"

    def ensure_directories(self) -> None:
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.raw_documents_path.mkdir(parents=True, exist_ok=True)
        self.processed_documents_path.mkdir(parents=True, exist_ok=True)
        self.auto_ingested_path.mkdir(parents=True, exist_ok=True)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    env_file = Path(__file__).resolve().parents[3] / ".env"
    settings = Settings(_env_file=env_file)
    settings.ensure_directories()
    return settings
