"""Schemas for the per-site connection (CMS credentials) endpoints."""
from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field

ConnectionType = Literal["crawler", "snippet", "wordpress", "shopify", "webflow", "github"]


class ConnectionCredentials(BaseModel):
    """Per-type credentials. Only the fields for the chosen type are required."""
    connection_type: ConnectionType

    # WordPress
    site_url: Optional[str] = None
    username: Optional[str] = None
    app_password: Optional[str] = None

    # Shopify
    shop_domain: Optional[str] = None
    access_token: Optional[str] = None

    # Webflow
    site_id: Optional[str] = None
    token: Optional[str] = None

    # GitHub
    owner: Optional[str] = None
    repo: Optional[str] = None
    branch: Optional[str] = "main"
    github_token: Optional[str] = None  # named separately to avoid clashing with Webflow `token`


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str


class ConnectionStatusResponse(BaseModel):
    connection_type: ConnectionType
    configured: bool
    last_tested_at: Optional[str] = None
    snippet_token: Optional[str] = None
    snippet_url: Optional[str] = None
