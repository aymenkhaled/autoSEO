"""Pydantic schemas for issues and fixes."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


class IssueResponse(BaseModel):
    id: UUID
    crawl_id: UUID
    site_id: UUID
    page_id: Optional[UUID] = None
    type: str
    category: str
    severity: str
    impact_score: int
    current_value: Optional[str] = None
    fix_type: str
    fix_status: str
    proposed_fix: Optional[str] = None
    proposed_fix_metadata: Optional[dict] = None
    ai_confidence: Optional[float] = None
    applied_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_score: Optional[int] = None
    rolled_back_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    issues: list[IssueResponse]
    total: int


class IssueFilter(BaseModel):
    site_id: Optional[UUID] = None
    crawl_id: Optional[UUID] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    fix_status: Optional[str] = None
    fix_type: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=200)


class FixApplyRequest(BaseModel):
    issue_id: UUID
    approved: bool = True


class FixRollbackRequest(BaseModel):
    issue_id: UUID


class FixResponse(BaseModel):
    issue_id: UUID
    status: str
    message: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


# --- Snippet Event ---
class SnippetEventCreate(BaseModel):
    token: UUID
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical: Optional[str] = None
    h1: Optional[str] = None
    schema: Optional[str] = None
    og_title: Optional[str] = None
    og_image: Optional[str] = None
    lcp: Optional[int] = None
    cls: Optional[float] = None
    ttfb: Optional[int] = None
    user_agent: Optional[str] = None
    viewport_width: Optional[int] = None
