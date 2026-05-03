"""Log import and crawl-budget insight helpers."""
from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tables import CrawlLogEntry, Page, SearchConsolePageMetric, Site

COMMON_LOG_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) [^"]+" (?P<status>\d{3}) (?P<bytes>\S+) "(?P<referrer>[^"]*)" "(?P<ua>[^"]*)"'
)

_CSV_MARKERS = {"clientrequesturi", "clientrequestmethod", "edgeresponsestatus", "user_agent", "useragent", "url"}


def bot_family(user_agent: str | None) -> str:
    ua = (user_agent or "").lower()
    if "googlebot" in ua:
        return "googlebot"
    if "bingbot" in ua:
        return "bingbot"
    if "slurp" in ua or "yahoo" in ua:
        return "yahoo"
    if "duckduckbot" in ua:
        return "duckduckbot"
    if "bot" in ua or "crawl" in ua or "spider" in ua:
        return "other_bot"
    return "human_or_unknown"


def _first(row: dict[str, Any], *names: str) -> Any:
    lower = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_datetime(value) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%d/%b/%Y:%H:%M:%S"):
        try:
            return datetime.strptime(text.split()[0], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _redact_url(url: str) -> str:
    """Drop query/fragment data because access logs often contain PII tokens."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))


def _absolute_url(value: str, *, site_domain: str) -> str:
    base = site_domain if site_domain.startswith(("http://", "https://")) else f"https://{site_domain}"
    parsed_base = urlparse(base)
    parsed_value = urlparse(value or "/")
    if parsed_value.scheme and parsed_value.netloc:
        return _redact_url(value)
    path = value if value.startswith("/") else f"/{value}"
    return _redact_url(f"{parsed_base.scheme}://{parsed_base.netloc}{path}")


def _entry_from_row(row: dict[str, Any], *, site_domain: str) -> dict[str, Any] | None:
    raw_url = _first(row, "ClientRequestURI", "request_uri", "uri", "url", "path", "cs-uri-stem")
    if not raw_url:
        return None
    user_agent = _first(row, "ClientRequestUserAgent", "user_agent", "userAgent", "ua", "cs(User-Agent)")
    status_code = _safe_int(_first(row, "EdgeResponseStatus", "status", "status_code", "sc-status"))
    return {
        "url": _absolute_url(str(raw_url), site_domain=site_domain),
        "method": str(_first(row, "ClientRequestMethod", "method", "cs-method") or "GET"),
        "status_code": status_code or 0,
        "user_agent": str(user_agent or ""),
        "bot_family": bot_family(str(user_agent or "")),
        "bytes_sent": _safe_int(_first(row, "EdgeResponseBytes", "bytes", "bytes_sent", "sc-bytes")),
        "requested_at": _safe_datetime(_first(row, "EdgeStartTimestamp", "timestamp", "time", "date")),
    }


def _parse_structured_logs(raw_log: str, *, site_domain: str, limit: int) -> tuple[list[dict[str, Any]], list[str]] | None:
    first_line = next((line for line in raw_log.splitlines() if line.strip()), "")
    if not first_line:
        return [], []
    entries: list[dict[str, Any]] = []
    errors: list[str] = []

    if first_line.lstrip().startswith("{"):
        for index, line in enumerate(raw_log.splitlines(), start=1):
            if len(entries) >= limit:
                errors.append(f"Stopped at {limit} rows to keep the import safe.")
                break
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"Line {index}: invalid JSON log row")
                continue
            entry = _entry_from_row(row, site_domain=site_domain)
            if entry:
                entries.append(entry)
            else:
                errors.append(f"Line {index}: missing URL/path field")
        return entries, errors[:50]

    header_tokens = {item.strip().lower() for item in first_line.split(",")}
    if header_tokens & _CSV_MARKERS:
        reader = csv.DictReader(io.StringIO(raw_log))
        for index, row in enumerate(reader, start=2):
            if len(entries) >= limit:
                errors.append(f"Stopped at {limit} rows to keep the import safe.")
                break
            entry = _entry_from_row(row, site_domain=site_domain)
            if entry:
                entries.append(entry)
            else:
                errors.append(f"Line {index}: missing URL/path field")
        return entries, errors[:50]

    return None


def parse_log_lines(raw_log: str, *, site_domain: str, limit: int = 5000) -> tuple[list[dict[str, Any]], list[str]]:
    structured = _parse_structured_logs(raw_log, site_domain=site_domain, limit=limit)
    if structured is not None:
        return structured

    base = site_domain if site_domain.startswith(("http://", "https://")) else f"https://{site_domain}"
    parsed_base = urlparse(base)
    entries: list[dict[str, Any]] = []
    errors: list[str] = []

    for index, line in enumerate(raw_log.splitlines(), start=1):
        if not line.strip():
            continue
        if len(entries) >= limit:
            errors.append(f"Stopped at {limit} rows to keep the import safe.")
            break
        match = COMMON_LOG_RE.search(line)
        if not match:
            errors.append(f"Line {index}: unsupported log format")
            continue
        path = match.group("path")
        parsed_path = urlparse(path)
        if parsed_path.scheme and parsed_path.netloc:
            url = _redact_url(path)
        else:
            url = _redact_url(f"{parsed_base.scheme}://{parsed_base.netloc}{path if path.startswith('/') else '/' + path}")
        status_code = int(match.group("status"))
        byte_text = match.group("bytes")
        try:
            bytes_sent = int(byte_text) if byte_text != "-" else None
        except ValueError:
            bytes_sent = None
        requested_at = _safe_datetime(match.group("time"))
        ua = match.group("ua")
        entries.append({
            "url": url,
            "method": match.group("method"),
            "status_code": status_code,
            "user_agent": ua,
            "bot_family": bot_family(ua),
            "bytes_sent": bytes_sent,
            "requested_at": requested_at,
        })

    return entries, errors[:50]


def summarize_log_entries(entries: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    by_bot = Counter(entry["bot_family"] for entry in entries)
    by_status = Counter(str(entry["status_code"]) for entry in entries)
    url_counts = Counter(entry["url"] for entry in entries)
    googlebot_urls = Counter(entry["url"] for entry in entries if entry["bot_family"] == "googlebot")
    waste_urls = [
        {"url": url, "hits": count}
        for url, count in googlebot_urls.most_common(20)
        if any(entry["url"] == url and (entry["status_code"] or 0) >= 400 for entry in entries)
    ]
    return {
        "rows": len(entries),
        "by_bot": dict(by_bot),
        "by_status": dict(by_status),
        "top_urls": [{"url": url, "hits": count} for url, count in url_counts.most_common(20)],
        "googlebot_error_urls": waste_urls,
        "errors": errors,
    }


async def crawl_budget_summary(db: AsyncSession, *, site: Site) -> dict[str, Any]:
    bot_rows = (
        await db.execute(
            select(CrawlLogEntry.bot_family, func.count(CrawlLogEntry.id))
            .where(CrawlLogEntry.site_id == site.id, CrawlLogEntry.org_id == site.org_id)
            .group_by(CrawlLogEntry.bot_family)
        )
    ).all()
    status_rows = (
        await db.execute(
            select(CrawlLogEntry.status_code, func.count(CrawlLogEntry.id))
            .where(CrawlLogEntry.site_id == site.id, CrawlLogEntry.org_id == site.org_id)
            .group_by(CrawlLogEntry.status_code)
        )
    ).all()
    googlebot_urls = {
        url: count
        for url, count in (
            await db.execute(
                select(CrawlLogEntry.url, func.count(CrawlLogEntry.id))
                .where(
                    CrawlLogEntry.site_id == site.id,
                    CrawlLogEntry.org_id == site.org_id,
                    CrawlLogEntry.bot_family == "googlebot",
                )
                .group_by(CrawlLogEntry.url)
                .order_by(func.count(CrawlLogEntry.id).desc())
                .limit(50)
            )
        ).all()
    }
    crawled_pages = {
        row[0]
        for row in (
            await db.execute(select(Page.url).where(Page.site_id == site.id, Page.org_id == site.org_id))
        ).all()
    }
    valuable_pages = {
        row[0]: float(row[1] or 0)
        for row in (
            await db.execute(
                select(SearchConsolePageMetric.page_url, func.sum(SearchConsolePageMetric.impressions))
                .where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == site.org_id)
                .group_by(SearchConsolePageMetric.page_url)
                .order_by(func.sum(SearchConsolePageMetric.impressions).desc())
                .limit(50)
            )
        ).all()
    }

    googlebot_not_crawled_by_autoseo = [url for url in googlebot_urls if url not in crawled_pages][:20]
    high_value_not_seen_by_googlebot = [
        {"url": url, "impressions": impressions}
        for url, impressions in valuable_pages.items()
        if url not in googlebot_urls
    ][:20]

    recommendations = []
    if high_value_not_seen_by_googlebot:
        recommendations.append("Important GSC pages do not appear in imported Googlebot logs; check internal links, sitemap freshness, and crawl blocking.")
    if googlebot_not_crawled_by_autoseo:
        recommendations.append("Googlebot is hitting URLs outside AutoSEO's crawl set; increase crawl coverage or check sitemap discovery.")
    if any((status or 0) >= 400 for status, _count in status_rows):
        recommendations.append("Fix Googlebot 4xx/5xx responses before lower-impact content work.")
    if not recommendations:
        recommendations.append("Import logs regularly to compare Googlebot behavior against AutoSEO crawl coverage and GSC value.")

    return {
        "site_id": str(site.id),
        "by_bot": {bot or "unknown": int(count) for bot, count in bot_rows},
        "by_status": {str(status or "unknown"): int(count) for status, count in status_rows},
        "googlebot_not_crawled_by_autoseo": googlebot_not_crawled_by_autoseo,
        "high_value_not_seen_by_googlebot": high_value_not_seen_by_googlebot,
        "recommendations": recommendations,
        "message": "Crawl-budget insights compare imported server logs with AutoSEO crawl coverage and GSC page value.",
    }
