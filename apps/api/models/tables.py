"""SQLAlchemy models for all AutoSEO database tables."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, SmallInteger, BigInteger,
    Numeric, ForeignKey, ARRAY, DateTime, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from models.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    plan = Column(Text, nullable=False, default="free")
    stripe_customer_id = Column(Text)
    stripe_subscription_id = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="organization")
    sites = relationship("Site", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    role = Column(Text, nullable=False, default="member")
    email = Column(Text, nullable=False)
    full_name = Column(Text)
    avatar_url = Column(Text)
    password_hash = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="users")


class Site(Base):
    __tablename__ = "sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(Text, nullable=False)
    domain = Column(Text, nullable=False)
    connection_type = Column(Text, nullable=False, default="crawler")
    cms_token_encrypted = Column(Text)
    cms_token_iv = Column(Text)
    cms_endpoint = Column(Text)
    github_installation_id = Column(BigInteger)
    github_repo = Column(Text)
    github_branch = Column(Text, default="main")
    snippet_token = Column(UUID(as_uuid=True), default=uuid.uuid4)
    gsc_property_url = Column(Text)
    gsc_token_encrypted = Column(Text)
    crawl_frequency = Column(Text, default="weekly")
    next_scheduled_crawl = Column(DateTime(timezone=True))
    crawl_max_pages = Column(Integer, default=500)
    respect_robots_txt = Column(Boolean, default=True)
    crawl_delay_ms = Column(Integer, default=1000)
    status = Column(Text, default="pending")
    ownership_verified = Column(Boolean, nullable=False, default=False)
    verification_method = Column(Text)
    verification_token = Column(Text)
    verification_requested_at = Column(DateTime(timezone=True))
    verified_at = Column(DateTime(timezone=True))
    last_crawled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="sites")
    crawls = relationship("Crawl", back_populates="site")


class Crawl(Base):
    __tablename__ = "crawls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    status = Column(Text, default="queued")
    trigger = Column(Text, default="scheduled")
    pages_crawled = Column(Integer, default=0)
    pages_total = Column(Integer)
    urls_discovered = Column(Integer, default=0)
    urls_skipped = Column(Integer, default=0)
    crawl_limit = Column(Integer)
    coverage_reason = Column(Text)
    coverage_details = Column(JSONB)
    issues_found = Column(Integer, default=0)
    seo_score = Column(SmallInteger)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    site = relationship("Site", back_populates="crawls")
    pages = relationship("Page", back_populates="crawl")
    issues = relationship("Issue", back_populates="crawl")

    __table_args__ = (
        Index("idx_crawls_site_id", "site_id"),
        Index("idx_crawls_org_id", "org_id"),
    )


class Page(Base):
    __tablename__ = "pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crawl_id = Column(UUID(as_uuid=True), ForeignKey("crawls.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    url = Column(Text, nullable=False)
    status_code = Column(SmallInteger)
    redirect_url = Column(Text)
    redirect_chain = Column(JSONB)
    crawl_depth = Column(SmallInteger)
    response_time_ms = Column(Integer)
    title = Column(Text)
    title_length = Column(SmallInteger)
    meta_description = Column(Text)
    meta_description_length = Column(SmallInteger)
    canonical_url = Column(Text)
    canonical_chain = Column(JSONB)
    robots_directive = Column(Text)
    h1_count = Column(SmallInteger)
    h1_text = Column(ARRAY(Text))
    h2_count = Column(SmallInteger)
    h3_count = Column(SmallInteger)
    heading_structure = Column(JSONB)
    word_count = Column(Integer)
    content_hash = Column(Text)
    internal_links_count = Column(Integer)
    external_links_count = Column(Integer)
    broken_links_count = Column(Integer)
    incoming_links_count = Column(Integer)
    images_count = Column(Integer)
    images_missing_alt = Column(Integer)
    images_large = Column(Integer)
    og_title = Column(Text)
    og_description = Column(Text)
    og_image = Column(Text)
    twitter_card = Column(Text)
    schema_types = Column(ARRAY(Text))
    schema_valid = Column(Boolean)
    schema_errors = Column(JSONB)
    lcp_ms = Column(Integer)
    fid_ms = Column(Integer)
    cls_score = Column(Numeric(4, 3))
    ttfb_ms = Column(Integer)
    performance_score = Column(SmallInteger)
    hreflang_tags = Column(JSONB)
    hreflang_errors = Column(ARRAY(Text))
    seo_score = Column(SmallInteger)
    # Gap 5: conditional GET cache headers (deferred → done)
    etag = Column(Text)
    last_modified = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    crawl = relationship("Crawl", back_populates="pages")
    issues = relationship("Issue", back_populates="page")
    page_sources = relationship("PageSource", back_populates="page")

    __table_args__ = (
        Index("idx_pages_crawl_id", "crawl_id"),
        Index("idx_pages_site_id", "site_id"),
        Index("idx_pages_org_id", "org_id"),
    )


class PageSource(Base):
    """Maps a crawled public URL to the real CMS resource identifier."""

    __tablename__ = "page_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id"))
    public_url = Column(Text, nullable=False)
    source_page_id = Column(Text, nullable=False)
    source_path = Column(Text)
    source_url = Column(Text)
    connection_type = Column(Text, nullable=False)
    source_metadata = Column("metadata", JSONB)
    last_synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    page = relationship("Page", back_populates="page_sources")

    __table_args__ = (
        Index("idx_page_sources_site_id", "site_id"),
        Index("idx_page_sources_page_id", "page_id"),
        Index("idx_page_sources_site_public_url", "site_id", "public_url", unique=True),
    )


class Issue(Base):
    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crawl_id = Column(UUID(as_uuid=True), ForeignKey("crawls.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id"))
    type = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    impact_score = Column(SmallInteger, nullable=False)
    current_value = Column(Text)
    fix_type = Column(Text, nullable=False, default="manual")
    fix_status = Column(Text, default="pending")
    proposed_fix = Column(Text)
    proposed_fix_metadata = Column(JSONB)
    ai_confidence = Column(Numeric(3, 2))
    applied_at = Column(DateTime(timezone=True))
    applied_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at = Column(DateTime(timezone=True))
    verified_score = Column(SmallInteger)
    rollback_value = Column(Text)
    rolled_back_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    crawl = relationship("Crawl", back_populates="issues")
    page = relationship("Page", back_populates="issues")

    __table_args__ = (
        Index("idx_issues_site_id", "site_id"),
        Index("idx_issues_org_id", "org_id"),
        Index("idx_issues_fix_status", "fix_status"),
        Index("idx_issues_site_status", "site_id", "fix_status"),
    )


class ChangeLog(Base):
    __tablename__ = "change_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"))
    action = Column(Text, nullable=False)
    actor_type = Column(Text, nullable=False)
    actor_id = Column(UUID(as_uuid=True))
    old_value = Column(Text)
    new_value = Column(Text)
    extra_metadata = Column("metadata", JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_change_log_site_id", "site_id"),
    )


class SnippetEvent(Base):
    __tablename__ = "snippet_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    page_url = Column(Text, nullable=False)
    title = Column(Text)
    meta_description = Column(Text)
    canonical_url = Column(Text)
    h1_text = Column(Text)
    schema_json = Column(Text)
    lcp_ms = Column(Integer)
    cls_score = Column(Numeric(4, 3))
    ttfb_ms = Column(Integer)
    inp_ms = Column(Integer)  # Phase 2 Gap 16 — INP is a Core Web Vital since 2024
    fcp_ms = Column(Integer)
    device_type = Column(Text)  # mobile|tablet|desktop — Gap 19
    user_agent = Column(Text)
    viewport_width = Column(SmallInteger)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_snippet_events_site_id", "site_id", "created_at"),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(Text, nullable=False)
    key_hash = Column(Text, nullable=False, unique=True)
    key_prefix = Column(Text, nullable=False)
    scopes = Column(ARRAY(Text), nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    keyword = Column(Text, nullable=False)
    target_url = Column(Text)
    intent = Column(Text, default="informational")
    priority = Column(SmallInteger, default=1)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    rankings = relationship("KeywordRanking", back_populates="keyword_ref", cascade="all, delete-orphan")


class KeywordRanking(Base):
    __tablename__ = "keyword_rankings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey("keywords.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    position = Column(SmallInteger)
    previous_position = Column(SmallInteger)
    search_volume = Column(Integer)
    cpc_usd = Column(Numeric(8, 2))
    difficulty = Column(SmallInteger)
    url = Column(Text)
    serp_features = Column(ARRAY(Text))
    country = Column(Text, default="US")
    device = Column(Text, default="desktop")
    checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    keyword_ref = relationship("Keyword", back_populates="rankings")


class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    domain = Column(Text, nullable=False)
    name = Column(Text)
    seo_score = Column(SmallInteger)
    keywords_count = Column(Integer)
    backlinks_count = Column(Integer)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_analyzed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Backlink(Base):
    __tablename__ = "backlinks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    source_url = Column(Text, nullable=False)
    source_domain = Column(Text, nullable=False)
    target_url = Column(Text, nullable=False)
    anchor_text = Column(Text)
    is_dofollow = Column(Boolean, default=True)
    domain_rating = Column(SmallInteger)
    is_new = Column(Boolean, default=False)
    is_lost = Column(Boolean, default=False)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    email = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default="member")
    status = Column(Text, nullable=False, default="pending")
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    invited_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    accepted_at = Column(DateTime(timezone=True))


class IssueComment(Base):
    __tablename__ = "issue_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text)
    data = Column(JSONB)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email_enabled = Column(Boolean, default=True)
    slack_enabled = Column(Boolean, default=False)
    in_app_enabled = Column(Boolean, default=True)
    slack_webhook_url = Column(Text)
    email_crawl_complete = Column(Boolean, default=True)
    email_new_issues = Column(Boolean, default=True)
    email_fix_applied = Column(Boolean, default=True)
    email_weekly_digest = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"))
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False, default="weekly")
    format = Column(Text, nullable=False, default="pdf")
    recipients = Column(ARRAY(Text), nullable=False)
    schedule_cron = Column(Text)
    last_sent_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    event_type = Column(Text, nullable=False)
    resource_type = Column(Text)
    resource_id = Column(UUID(as_uuid=True))
    event_metadata = Column("metadata", JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    secret = Column(Text, nullable=False)
    events = Column(ARRAY(Text), nullable=False)
    enabled = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    event = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    status_code = Column(SmallInteger)
    response_body = Column(Text)
    duration_ms = Column(Integer)
    success = Column(Boolean)
    attempted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    next_retry_at = Column(DateTime(timezone=True))

    webhook = relationship("Webhook", back_populates="deliveries")


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    model = Column(Text, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Numeric(10, 6), nullable=False, default=0)
    task_type = Column(Text)
    crawl_id = Column(UUID(as_uuid=True), ForeignKey("crawls.id"))
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))



class FixVersion(Base):
    """Gap 22 (deferred → done): snapshot of an issue's value before each fix.

    Every apply writes one row, giving us an authoritative version history
    independent of the (mutable) `issues.rollback_value` field.
    """
    __tablename__ = "fix_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    captured_value = Column(Text)         # value before the fix was applied
    applied_value = Column(Text)          # value written by the fix
    applied_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(Text, nullable=False, default="apply")  # apply | rollback
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_fix_versions_issue_id", "issue_id"),
        Index("idx_fix_versions_site_id", "site_id"),
    )


class SearchConsoleConnection(Base):
    __tablename__ = "search_console_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    property_url = Column(Text, nullable=False)
    token_encrypted = Column(Text, nullable=False)
    token_iv = Column(Text, nullable=False)
    scopes = Column(ARRAY(Text), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    connected_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_sync_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_search_console_connections_site", "site_id", unique=True),
        Index("idx_search_console_connections_org", "org_id"),
    )


class SearchConsoleSyncRun(Base):
    __tablename__ = "search_console_sync_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("search_console_connections.id"))
    status = Column(Text, nullable=False, default="running")
    days = Column(Integer, nullable=False, default=90)
    pages_synced = Column(Integer, nullable=False, default=0)
    queries_synced = Column(Integer, nullable=False, default=0)
    inspections_synced = Column(Integer, nullable=False, default=0)
    sitemaps_synced = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_search_console_sync_runs_site", "site_id", "created_at"),
    )


class SearchConsolePageMetric(Base):
    __tablename__ = "search_console_page_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    sync_run_id = Column(UUID(as_uuid=True), ForeignKey("search_console_sync_runs.id"))
    page_url = Column(Text, nullable=False)
    date_start = Column(Text, nullable=False)
    date_end = Column(Text, nullable=False)
    device = Column(Text)
    country = Column(Text)
    clicks = Column(Numeric(12, 2), nullable=False, default=0)
    impressions = Column(Numeric(12, 2), nullable=False, default=0)
    ctr = Column(Numeric(8, 6), nullable=False, default=0)
    position = Column(Numeric(8, 3), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_gsc_page_metrics_site_page", "site_id", "page_url"),
        Index("idx_gsc_page_metrics_site_impressions", "site_id", "impressions"),
    )


class SearchConsoleQueryMetric(Base):
    __tablename__ = "search_console_query_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    sync_run_id = Column(UUID(as_uuid=True), ForeignKey("search_console_sync_runs.id"))
    page_url = Column(Text)
    query = Column(Text, nullable=False)
    date_start = Column(Text, nullable=False)
    date_end = Column(Text, nullable=False)
    device = Column(Text)
    country = Column(Text)
    clicks = Column(Numeric(12, 2), nullable=False, default=0)
    impressions = Column(Numeric(12, 2), nullable=False, default=0)
    ctr = Column(Numeric(8, 6), nullable=False, default=0)
    position = Column(Numeric(8, 3), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_gsc_query_metrics_site_query", "site_id", "query"),
        Index("idx_gsc_query_metrics_site_page", "site_id", "page_url"),
    )


class SearchConsoleInspection(Base):
    __tablename__ = "search_console_inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    sync_run_id = Column(UUID(as_uuid=True), ForeignKey("search_console_sync_runs.id"))
    url = Column(Text, nullable=False)
    verdict = Column(Text)
    coverage_state = Column(Text)
    indexing_state = Column(Text)
    robots_txt_state = Column(Text)
    page_fetch_state = Column(Text)
    last_crawl_time = Column(Text)
    google_canonical = Column(Text)
    user_canonical = Column(Text)
    raw = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_gsc_inspections_site_url", "site_id", "url"),
    )


class SearchConsoleSitemap(Base):
    __tablename__ = "search_console_sitemaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    sync_run_id = Column(UUID(as_uuid=True), ForeignKey("search_console_sync_runs.id"))
    path = Column(Text, nullable=False)
    is_pending = Column(Boolean)
    is_sitemaps_index = Column(Boolean)
    last_submitted = Column(Text)
    last_downloaded = Column(Text)
    errors = Column(Integer, default=0)
    warnings = Column(Integer, default=0)
    raw = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_gsc_sitemaps_site_path", "site_id", "path"),
    )


class SiteOpportunity(Base):
    __tablename__ = "site_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    source = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    priority_score = Column(Integer, nullable=False, default=0)
    impact_label = Column(Text)
    affected_url = Column(Text)
    issue_type = Column(Text)
    data = Column(JSONB)
    status = Column(Text, nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_site_opportunities_site_priority", "site_id", "priority_score"),
        Index("idx_site_opportunities_site_status", "site_id", "status"),
    )


class ConnectionCertification(Base):
    __tablename__ = "connection_certifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    connection_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="sandbox_only")
    message = Column(Text)
    details = Column(JSONB)
    last_tested_at = Column(DateTime(timezone=True))
    safe_fix_tested_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_connection_certifications_site_type", "site_id", "connection_type", unique=True),
    )


class SnippetInsight(Base):
    __tablename__ = "snippet_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    page_url = Column(Text)
    insight_type = Column(Text, nullable=False)
    severity = Column(Text, nullable=False, default="medium")
    device_type = Column(Text)
    metric_name = Column(Text)
    metric_value = Column(Numeric(12, 3))
    sample_size = Column(Integer, nullable=False, default=0)
    title = Column(Text, nullable=False)
    description = Column(Text)
    data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_snippet_insights_site_type", "site_id", "insight_type"),
    )


class GoogleAnalyticsConnection(Base):
    __tablename__ = "google_analytics_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    property_id = Column(Text, nullable=False)
    property_name = Column(Text)
    token_encrypted = Column(Text, nullable=False)
    token_iv = Column(Text, nullable=False)
    scopes = Column(ARRAY(Text), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    connected_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_sync_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_google_analytics_connections_site", "site_id", unique=True),
        Index("idx_google_analytics_connections_org", "org_id"),
    )


class GoogleAnalyticsSyncRun(Base):
    __tablename__ = "google_analytics_sync_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("google_analytics_connections.id"))
    status = Column(Text, nullable=False, default="running")
    days = Column(Integer, nullable=False, default=90)
    rows_synced = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_google_analytics_sync_runs_site", "site_id", "created_at"),
    )


class AnalyticsPageMetric(Base):
    __tablename__ = "analytics_page_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    sync_run_id = Column(UUID(as_uuid=True), ForeignKey("google_analytics_sync_runs.id"))
    page_url = Column(Text, nullable=False)
    date_start = Column(Text, nullable=False)
    date_end = Column(Text, nullable=False)
    sessions = Column(Numeric(12, 2), nullable=False, default=0)
    active_users = Column(Numeric(12, 2), nullable=False, default=0)
    views = Column(Numeric(12, 2), nullable=False, default=0)
    key_events = Column(Numeric(12, 2), nullable=False, default=0)
    total_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    transactions = Column(Numeric(12, 2), nullable=False, default=0)
    engagement_rate = Column(Numeric(8, 6), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_analytics_page_metrics_site_page", "site_id", "page_url"),
        Index("idx_analytics_page_metrics_site_revenue", "site_id", "total_revenue"),
    )


class PageSpeedRun(Base):
    __tablename__ = "pagespeed_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    page_url = Column(Text, nullable=False)
    strategy = Column(Text, nullable=False, default="mobile")
    status = Column(Text, nullable=False, default="running")
    performance_score = Column(SmallInteger)
    accessibility_score = Column(SmallInteger)
    best_practices_score = Column(SmallInteger)
    seo_score = Column(SmallInteger)
    lcp_ms = Column(Integer)
    inp_ms = Column(Integer)
    cls_score = Column(Numeric(6, 4))
    fcp_ms = Column(Integer)
    ttfb_ms = Column(Integer)
    total_blocking_time_ms = Column(Integer)
    speed_index_ms = Column(Integer)
    opportunities = Column(JSONB)
    diagnostics = Column(JSONB)
    crux_metrics = Column(JSONB)
    screenshot = Column(Text)
    error_message = Column(Text)
    checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_pagespeed_runs_site_url", "site_id", "page_url", "strategy"),
        Index("idx_pagespeed_runs_site_checked", "site_id", "checked_at"),
    )


class IndexNowKey(Base):
    __tablename__ = "indexnow_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    key = Column(Text, nullable=False)
    key_location = Column(Text, nullable=False)
    verified = Column(Boolean, nullable=False, default=False)
    last_verified_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_indexnow_keys_site", "site_id", unique=True),
    )


class IndexNowSubmission(Base):
    __tablename__ = "indexnow_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    key_id = Column(UUID(as_uuid=True), ForeignKey("indexnow_keys.id"))
    urls = Column(ARRAY(Text), nullable=False)
    status_code = Column(SmallInteger)
    success = Column(Boolean)
    response_body = Column(Text)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_indexnow_submissions_site", "site_id", "created_at"),
    )


class CompetitorPageComparison(Base):
    __tablename__ = "competitor_page_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    competitor_id = Column(UUID(as_uuid=True), ForeignKey("competitors.id"), nullable=False)
    site_page_url = Column(Text, nullable=False)
    competitor_page_url = Column(Text, nullable=False)
    site_score = Column(SmallInteger)
    competitor_score = Column(SmallInteger)
    gaps = Column(JSONB)
    site_signals = Column(JSONB)
    competitor_signals = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_competitor_page_comparisons_competitor", "competitor_id", "created_at"),
    )


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(Text, nullable=False)
    contact_email = Column(Text)
    brand_name = Column(Text)
    logo_url = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_clients_org", "org_id"),
    )


class ReportShareLink(Base):
    __tablename__ = "report_share_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    token = Column(Text, nullable=False, unique=True)
    title = Column(Text, nullable=False)
    snapshot = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_report_share_links_site", "site_id", "created_at"),
    )


class FixProofSnapshot(Base):
    __tablename__ = "fix_proof_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    issue_type = Column(Text)
    snapshot_type = Column(Text, nullable=False)  # before_pr | after_recrawl | after_7_days | after_28_days | manual
    pr_url = Column(Text)
    branch = Column(Text)
    seo_score = Column(SmallInteger)
    pages_crawled = Column(Integer, default=0)
    open_issue_count = Column(Integer, default=0)
    grouped_issue_count = Column(Integer, default=0)
    gsc_clicks = Column(Numeric(12, 2), default=0)
    gsc_impressions = Column(Numeric(12, 2), default=0)
    gsc_ctr = Column(Numeric(8, 6), default=0)
    gsc_position = Column(Numeric(8, 3), default=0)
    ga_sessions = Column(Numeric(12, 2), default=0)
    ga_key_events = Column(Numeric(12, 2), default=0)
    ga_revenue = Column(Numeric(12, 2), default=0)
    pagespeed_score = Column(SmallInteger)
    evidence = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_fix_proof_snapshots_site_created", "site_id", "created_at"),
        Index("idx_fix_proof_snapshots_site_issue", "site_id", "issue_type"),
    )


class AutopilotRun(Base):
    __tablename__ = "autopilot_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"))
    status = Column(Text, nullable=False, default="completed")
    run_type = Column(Text, nullable=False, default="manual")
    summary = Column(Text)
    next_actions = Column(JSONB)
    provider_health = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_autopilot_runs_org_created", "org_id", "created_at"),
        Index("idx_autopilot_runs_site_created", "site_id", "created_at"),
    )


class AiVisibilityPrompt(Base):
    __tablename__ = "ai_visibility_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    target_entity = Column(Text)
    competitor_domains = Column(ARRAY(Text))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_ai_visibility_prompts_site", "site_id", "created_at"),
    )


class AiVisibilityRun(Base):
    __tablename__ = "ai_visibility_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("ai_visibility_prompts.id"))
    prompt = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="completed")
    visibility_score = Column(SmallInteger)
    entity_score = Column(SmallInteger)
    citation_score = Column(SmallInteger)
    competitor_mentions = Column(JSONB)
    missing_context = Column(JSONB)
    recommendations = Column(JSONB)
    evidence = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_ai_visibility_runs_site_created", "site_id", "created_at"),
    )


class ContentBrief(Base):
    __tablename__ = "content_briefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    source_opportunity_id = Column(UUID(as_uuid=True), ForeignKey("site_opportunities.id"))
    page_url = Column(Text, nullable=False)
    target_keyword = Column(Text)
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="brief_ready")
    brief = Column(JSONB, nullable=False)
    github_pr_url = Column(Text)
    github_branch = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_content_briefs_site_created", "site_id", "created_at"),
    )


class KeywordProviderSyncRun(Base):
    __tablename__ = "keyword_provider_sync_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    provider = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="skipped_provider_missing")
    keywords_synced = Column(Integer, nullable=False, default=0)
    message = Column(Text)
    data = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_keyword_provider_sync_runs_site", "site_id", "created_at"),
    )


class CrawlLogImport(Base):
    __tablename__ = "crawl_log_imports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    filename = Column(Text)
    status = Column(Text, nullable=False, default="completed")
    rows_ingested = Column(Integer, nullable=False, default=0)
    summary = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_crawl_log_imports_site_created", "site_id", "created_at"),
    )


class CrawlLogEntry(Base):
    __tablename__ = "crawl_log_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    import_id = Column(UUID(as_uuid=True), ForeignKey("crawl_log_imports.id"), nullable=False)
    url = Column(Text, nullable=False)
    method = Column(Text)
    status_code = Column(SmallInteger)
    user_agent = Column(Text)
    bot_family = Column(Text)
    bytes_sent = Column(Integer)
    requested_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_crawl_log_entries_site_url", "site_id", "url"),
        Index("idx_crawl_log_entries_site_bot", "site_id", "bot_family"),
    )


class ClientSite(Base):
    __tablename__ = "client_sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_client_sites_client_site", "client_id", "site_id", unique=True),
        Index("idx_client_sites_org", "org_id"),
    )
