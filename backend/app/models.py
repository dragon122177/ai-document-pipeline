from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .utils import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class Role(StrEnum):
    admin = "ADMIN"
    analyst = "ANALYST"
    reviewer = "REVIEWER"


class DocumentStatus(StrEnum):
    queued = "QUEUED"
    processing = "PROCESSING"
    completed = "COMPLETED"
    needs_review = "NEEDS_REVIEW"
    approved = "APPROVED"
    rejected = "REJECTED"
    failed = "FAILED"


class JobStatus(StrEnum):
    queued = "QUEUED"
    processing = "PROCESSING"
    completed = "COMPLETED"
    needs_review = "NEEDS_REVIEW"
    failed = "FAILED"
    cancelled = "CANCELLED"


class ReviewStatus(StrEnum):
    pending = "PENDING"
    approved = "APPROVED"
    rejected = "REJECTED"


class LoginRequest(ApiModel):
    email: str = Field(min_length=3, max_length=180)
    password: str = Field(min_length=6, max_length=128)


class UserPublic(ApiModel):
    id: str
    email: str
    name: str
    role: Role


class SessionResponse(ApiModel):
    token: str
    user: UserPublic


class TextDocumentCreate(ApiModel):
    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=20, max_length=250_000)
    tags: list[str] = Field(default_factory=list, max_length=12)
    idempotency_key: str | None = Field(default=None, max_length=120)


class Entity(ApiModel):
    type: str
    value: str
    start: int
    end: int
    confidence: float = Field(ge=0, le=1)


class RiskFlag(ApiModel):
    severity: str
    code: str
    message: str


class DocumentListItem(ApiModel):
    id: str
    title: str
    file_name: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    category: str | None = None
    language: str | None = None
    page_count: int
    confidence: float | None = None
    tags: list[str] = Field(default_factory=list)
    created_by_name: str
    created_at: str
    updated_at: str


class DocumentDetail(DocumentListItem):
    sha256: str
    raw_text: str
    redacted_text: str
    summary: str
    keywords: list[str]
    entities: list[Entity]
    fields: dict[str, Any]
    risk_flags: list[RiskFlag]
    job: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)


class DocumentCreateResponse(ApiModel):
    document: DocumentListItem
    job_id: str
    deduplicated: bool = False


class JobResponse(ApiModel):
    id: str
    document_id: str
    document_title: str
    status: JobStatus
    current_stage: str
    progress: int
    attempt: int
    max_retries: int
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class ReviewDecision(ApiModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    notes: str = Field(default="", max_length=2_000)
    corrections: dict[str, Any] = Field(default_factory=dict)


class ReviewItem(ApiModel):
    id: str
    document_id: str
    document_title: str
    category: str | None = None
    confidence: float | None = None
    status: ReviewStatus
    assigned_to_name: str | None = None
    notes: str | None = None
    corrections: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    created_at: str
    decided_at: str | None = None


class SearchResult(ApiModel):
    document_id: str
    title: str
    category: str | None = None
    status: DocumentStatus
    snippet: str
    rank: float
    updated_at: str


class TemplateResponse(ApiModel):
    id: str
    name: str
    document_type: str
    description: str
    fields: list[dict[str, Any]]
    active: bool
    created_at: str


class AuditEventResponse(ApiModel):
    id: str
    actor_name: str | None = None
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: str
    metadata: dict[str, Any]
    created_at: str


class DashboardResponse(ApiModel):
    metrics: dict[str, int | float]
    category_distribution: list[dict[str, Any]]
    recent_documents: list[DocumentListItem]
    active_jobs: list[JobResponse]
    review_queue: list[ReviewItem]
    generated_at: str
