"""Pydantic schemas for site management."""
from pydantic import BaseModel, Field, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=500)
    connection_type: str = Field(default="crawler", pattern="^(crawler|wordpress|shopify|webflow|github|snippet)$")
    cms_endpoint: Optional[str] = None
    github_repo: Optional[str] = None
    github_branch: Optional[str] = "main"
    crawl_frequency: str = Field(default="weekly", pattern="^(daily|weekly|biweekly|monthly)$")
    crawl_max_pages: int = Field(default=500, ge=1, le=50000)
    respect_robots_txt: bool = True
    crawl_delay_ms: int = Field(default=1000, ge=500, le=10000)


class SiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    connection_type: Optional[str] = Field(None, pattern="^(crawler|wordpress|shopify|webflow|github|snippet)$")
    cms_endpoint: Optional[str] = None
    crawl_frequency: Optional[str] = Field(None, pattern="^(daily|weekly|biweekly|monthly)$")
    crawl_max_pages: Optional[int] = Field(None, ge=1, le=50000)
    respect_robots_txt: Optional[bool] = None
    crawl_delay_ms: Optional[int] = Field(None, ge=500, le=10000)


class SiteResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    domain: str
    connection_type: str
    cms_endpoint: Optional[str] = None
    github_repo: Optional[str] = None
    github_branch: Optional[str] = None
    snippet_token: Optional[UUID] = None
    crawl_frequency: str
    crawl_max_pages: int
    respect_robots_txt: bool
    crawl_delay_ms: int
    status: str
    last_crawled_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SiteListResponse(BaseModel):
    sites: list[SiteResponse]
    total: int


class CMSDetectionResponse(BaseModel):
    domain: str
    detected_cms: Optional[str] = None
    cms_version: Optional[str] = None
    seo_plugin: Optional[str] = None
    recommended_connection: str
    instructions: str
