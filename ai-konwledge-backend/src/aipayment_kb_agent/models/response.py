from __future__ import annotations

from pydantic import BaseModel, Field


class SourceScores(BaseModel):
    relevance: float
    vectorSim: float
    vectorDistance: float
    rerank: float
    bm25: float


class SourceEntity(BaseModel):
    text: str
    type: str


class SourceHit(BaseModel):
    id: str
    rank: int
    docTitle: str
    docType: str
    collection: str
    author: str | None = None
    updatedAt: str
    page: int | None = None
    section: str | None = None
    url: str | None = None
    sourcePath: str | None = None
    snippet: str
    highlights: list[str] = Field(default_factory=list)
    scores: SourceScores
    summary: str
    bullets: list[str] = Field(default_factory=list)
    entities: list[SourceEntity] = Field(default_factory=list)
    tokens: int = 0


class RetrievalMeta(BaseModel):
    totalMs: int
    embedMs: int
    searchMs: int
    rerankMs: int
    generateMs: int
    embedModel: str
    rerankModel: str
    llmModel: str
    strategy: str
    topK: int
    candidatesScanned: int
    promptTokens: int
    completionTokens: int
    temperature: float
    fallbackUsed: bool = False


class UpgradeDecision(BaseModel):
    enabled: bool
    candidateId: str | None = None
    status: str | None = None
    message: str | None = None


class FileMatch(BaseModel):
    title: str
    sourcePath: str
    category: str = "general"
    docType: str = "note"
    updatedAt: str = ""
    chunks: int = 0
    score: float = 0.0
    preview: str = ""


class QueryResponse(BaseModel):
    message_id: str
    session_id: str
    role: str = "assistant"
    content: str
    createdAt: str
    hits: list[SourceHit] = Field(default_factory=list)
    meta: RetrievalMeta
    citationOrder: list[str] = Field(default_factory=list)
    upgradeDecision: UpgradeDecision | None = None
    canAddToKnowledge: bool = False
    answerMode: str = "knowledge_qa"
    fileMatches: list[FileMatch] = Field(default_factory=list)


class UpgradeCandidate(BaseModel):
    candidate_id: str
    question: str
    answer: str
    title: str
    category: str
    tags: list[str] = Field(default_factory=list)
    markdown_path: str
    status: str
    created_at: str
