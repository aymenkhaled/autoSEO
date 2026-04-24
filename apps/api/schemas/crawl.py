"""Pydantic schemas for crawls."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class CrawlCreate(BaseModel):
    site_id: UUID
    trigger: str = Field(default="manual", pattern="^(manual|scheduled|webhook)$")


class CrawlResponse(BaseModel):
    id: UUID
    site_id: UUID
    org_id: UUID
    status: str
    trigger: str
    pages_crawled: int
    pages_total: Optional[int] = None
    urls_discovered: int = 0
    urls_skipped: int = 0
    crawl_limit: Optional[int] = None
    coverage_reason: Optional[str] = None
    coverage_details: Optional[dict] = None
    issues_found: int
    seo_score: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrawlListResponse(BaseModel):
    crawls: list[CrawlResponse]
    total: int


class CrawlProgress(BaseModel):
    """SSE progress update."""
    crawl_id: UUID
    status: str
    pages_crawled: int
    pages_total: Optional[int] = None
    urls_discovered: int = 0
    urls_skipped: int = 0
    crawl_limit: Optional[int] = None
    coverage_reason: Optional[str] = None
    current_url: Optional[str] = None
    percentage: Optional[float] = None
