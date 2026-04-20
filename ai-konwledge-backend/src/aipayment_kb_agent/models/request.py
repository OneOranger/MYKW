from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    session_id: str = Field(default="default")
    message: str = Field(min_length=1)
    auto_upgrade: bool = Field(default=False)
    top_k: int | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class UpgradeReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    reviewer: str = "user"
    note: str | None = None


class TriggerUpgradeRequest(BaseModel):
    session_id: str = "default"
    candidate_limit: int = 5


class UpgradeCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class UpgradeBatchReviewRequest(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list)
    action: str = Field(pattern="^(approve|reject)$")
    reviewer: str = "user"
    note: str | None = None


class RevealPathRequest(BaseModel):
    path: str = Field(min_length=1)


class RuntimeRetrievalConfigUpdateRequest(BaseModel):
    top_k: int | None = Field(default=None, ge=1, le=50)
