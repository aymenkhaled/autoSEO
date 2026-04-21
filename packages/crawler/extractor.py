"""SEO signal extractor — parses HTML and extracts all spec-defined signals.

Phase 2 enhancements (from gap analysis):
- Gap 7: Threads HTTP response headers (X-Robots-Tag, HSTS, Cache-Control)
- Gap 8: Generates issues for HTTP 4xx/5xx pages
- Gap 9: Page-type-aware thin-content thresholds
- Gap 10: Heading hierarchy violation detection
- Gap 11: Non-modern image format detection (jpg/png vs webp/avif)
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup


# Page-type-aware thin content thresholds (Gap 9)
THIN_CONTENT_THRESHOLDS = {
    "product": 200,
    "article": 500,
    "homepage": 100,
    "utility": 30,   # contact / about / team
    "category": 150,
    "generic": 250,
}

MODERN_IMAGE_EXTS = {"webp", "avif", "svg"}
NON_MODERN_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff"}


def classify_page_type(url: str, schema_types: list[str] | None) -> str:
    """Classify a page so we can apply appropriate quality thresholds."""
    schema_types = schema_types or []
    schemas_lower = [str(s).lower() for s in schema_types]

    if any("product" in s for s in schemas_lower):
        return "product"
    if any(s in ("article", "blogposting", "newsarticle") for s in schemas_lower):
        return "article"
    if any("faqpage" in s for s in schemas_lower):
        return "article"

    url_lower = url.lower()
    parsed = urlparse(url_lower)
    path = parsed.path.rstrip("/")

    if not path:
        return "homepage"
    if any(seg in path for seg in ("/contact", "/about", "/team", "/privacy", "/terms", "/legal")):
        return "utility"
    if any(seg in path for seg in ("/blog/", "/news/", "/articles/", "/posts/")):
        return "article"
    if any(seg in path for seg in ("/category/", "/tag/", "/categories/", "/topics/")):
        return "category"
    if path.count("/") <= 1:
        return "homepage"
    return "generic"


class SEOExtractor:
    def __init__(self, html: str, url: str, headers: dict | None = None):
        self.soup = BeautifulSoup(html or "", "lxml")
        self.url = url
        self.base_domain = urlparse(url).netloc
        self.headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}

    def extract_all(self) -> dict:
        return {
            **self._meta(),
            **self._headings(),
            **self._links(),
            **self._images(),
            **self._schema(),
            **self._social(),
            **self._technical(),
            **self._http_headers(),
        }

    def _meta(self) -> dict:
        title_tag = self.soup.find("title")
        desc_tag = self.soup.find("meta", attrs={"name": "description"})
        canonical_tag = self.soup.find("link", attrs={"rel": "canonical"})
        robots_tag = self.soup.find("meta", attrs={"name": "robots"})
        viewport_tag = self.soup.find("meta", attrs={"name": "viewport"})
        html_tag = self.soup.find("html")

        t = title_tag.get_text(strip=True) if title_tag else None
        d = desc_tag.get("content", "").strip() if desc_tag else None
        return {
            "title": t,
            "title_length": len(t) if t else 0,
            "meta_description": d,
            "meta_description_length": len(d) if d else 0,
            "canonical_url": canonical_tag.get("href") if canonical_tag else None,
            "robots_directive": robots_tag.get("content") if robots_tag else "index, follow",
            "has_viewport": viewport_tag is not None,
            "html_lang": html_tag.get("lang") if html_tag else None,
        }

    def _headings(self) -> dict:
        h1s = self.soup.find_all("h1")
        h2s = self.soup.find_all("h2")
        h3s = self.soup.find_all("h3")
        structure = []
        for tag in self.soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            structure.append({
                "level": int(tag.name[1]),
                "text": tag.get_text(strip=True)[:200],
            })

        # Gap 10: Detect heading hierarchy violations (e.g. H1 → H3)
        hierarchy_skips = []
        prev_level = 0
        for h in structure:
            level = h["level"]
            if prev_level and level > prev_level + 1:
                hierarchy_skips.append(f"H{prev_level} → H{level} (skipped)")
            prev_level = level

        return {
            "h1_count": len(h1s),
            "h1_text": [h.get_text(strip=True) for h in h1s],
            "h2_count": len(h2s),
            "h3_count": len(h3s),
            "heading_structure": structure[:50],
            "heading_hierarchy_skips": hierarchy_skips,
        }

    def _links(self) -> dict:
        links = self.soup.find_all("a", href=True)
        internal = []
        external = []
        nofollow_internal = []
        for l in links:
            href = (l.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            parsed = urlparse(href)
            rel = " ".join(l.get("rel") or []).lower()
            if parsed.netloc in ("", self.base_domain):
                internal.append(href)
                if "nofollow" in rel:
                    nofollow_internal.append(href)
            elif parsed.scheme in ("http", "https"):
                external.append(href)
        return {
            "internal_links_count": len(internal),
            "external_links_count": len(external),
            "broken_links_count": 0,  # populated by orchestrator from HTTP results
            "internal_nofollow_count": len(nofollow_internal),
        }

    def _images(self) -> dict:
        imgs = self.soup.find_all("img")
        missing_alt = 0
        non_modern_format = 0
        for i in imgs:
            if not (i.get("alt") or "").strip():
                missing_alt += 1
            src = (i.get("src") or i.get("data-src") or "").strip()
            if not src or src.startswith("data:"):
                continue
            ext = src.split("?")[0].split("#")[0].rsplit(".", 1)[-1].lower()
            if ext in NON_MODERN_IMAGE_EXTS:
                # Check srcset for modern fallbacks
                srcset = i.get("srcset", "") or ""
                if not any(m in srcset.lower() for m in MODERN_IMAGE_EXTS):
                    non_modern_format += 1
        return {
            "images_count": len(imgs),
            "images_missing_alt": missing_alt,
            "images_large": 0,
            "images_non_modern_format": non_modern_format,
        }

    def _schema(self) -> dict:
        schemas, types, errors = [], [], []
        for s in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "")
                schemas.append(data)
                if isinstance(data, dict) and "@type" in data:
                    t = data["@type"]
                    types.extend(t if isinstance(t, list) else [t])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "@type" in item:
                            t = item["@type"]
                            types.extend(t if isinstance(t, list) else [t])
            except (json.JSONDecodeError, ValueError) as e:
                errors.append(str(e))
        return {
            "schema_types": [str(t) for t in types],
            "schema_valid": len(errors) == 0,
            "schema_errors": errors if errors else None,
        }

    def _social(self) -> dict:
        def og(prop):
            tag = self.soup.find("meta", attrs={"property": f"og:{prop}"})
            return tag.get("content") if tag else None

        def tw(name):
            tag = self.soup.find("meta", attrs={"name": f"twitter:{name}"})
            return tag.get("content") if tag else None

        return {
            "og_title": og("title"),
            "og_description": og("description"),
            "og_image": og("image"),
            "twitter_card": tw("card"),
        }

    def _technical(self) -> dict:
        hreflang_tags = self.soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
        hreflang = [{"lang": t.get("hreflang"), "href": t.get("href")} for t in hreflang_tags]
        text = self.soup.get_text(separator=" ")
        # Better word splitting — avoid counting punctuation
        words = re.findall(r"\b\w+\b", text)
        return {
            "hreflang_tags": hreflang if hreflang else None,
            "hreflang_errors": [],
            "word_count": len(words),
        }

    def _http_headers(self) -> dict:
        """Gap 7: extract SEO-relevant HTTP response headers."""
        h = self.headers
        return {
            "x_robots_tag": h.get("x-robots-tag"),
            "hsts": h.get("strict-transport-security") is not None,
            "content_type": h.get("content-type"),
            "cache_control": h.get("cache-control"),
            "http_canonical": _parse_link_header_canonical(h.get("link")),
        }


def _parse_link_header_canonical(link_header: str | None) -> str | None:
    if not link_header:
        return None
    # Format: <https://example.com/canonical>; rel="canonical"
    for part in link_header.split(","):
        if "rel=\"canonical\"" in part or "rel=canonical" in part:
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Scoring
# ──────────────────────────────────────────────────────────────────────────────

def calculate_page_score(signals: dict) -> int:
    """Weighted SEO score 0–100 based on extracted signals."""
    status = signals.get("status_code", 200) or 200
    if status == 404 or status == 410:
        return 0
    if status >= 500:
        return 10

    score = 100
    deductions = []

    title = signals.get("title")
    title_len = signals.get("title_length", 0)
    if not title:
        deductions.append(15)
    elif title_len < 30 or title_len > 60:
        deductions.append(8)

    desc = signals.get("meta_description")
    desc_len = signals.get("meta_description_length", 0)
    if not desc:
        deductions.append(10)
    elif desc_len < 70 or desc_len > 160:
        deductions.append(5)

    h1_count = signals.get("h1_count", 0)
    if h1_count == 0:
        deductions.append(10)
    elif h1_count > 1:
        deductions.append(5)

    if signals.get("heading_hierarchy_skips"):
        deductions.append(3)

    if signals.get("images_missing_alt", 0) > 0:
        ratio = min(signals["images_missing_alt"] / max(signals.get("images_count", 1), 1), 1.0)
        deductions.append(int(ratio * 10))

    if signals.get("images_non_modern_format", 0) > 5:
        deductions.append(4)

    if not signals.get("schema_types"):
        deductions.append(5)

    if not (signals.get("canonical_url") or signals.get("http_canonical")):
        deductions.append(5)

    page_type = signals.get("page_type") or "generic"
    threshold = THIN_CONTENT_THRESHOLDS.get(page_type, 250)
    if signals.get("word_count", 0) < threshold:
        deductions.append(5)

    return max(0, score - sum(deductions))


# ──────────────────────────────────────────────────────────────────────────────
# Issue generation
# ──────────────────────────────────────────────────────────────────────────────

def generate_issues(pages: list[dict]) -> list[dict]:
    """Generate issue records from extracted page signals."""
    issues = []
    for page in pages:
        url = page.get("url", "")
        page_id = page.get("_page_id")
        status = page.get("status_code", 200) or 200
        page_type = page.get("page_type") or classify_page_type(url, page.get("schema_types"))

        # Gap 8: HTTP status code issues take precedence
        if status in (404, 410):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "http_404", "category": "technical",
                "severity": "high", "impact_score": 80,
                "current_value": str(status),
                "fix_type": "manual",
            })
            continue
        if status >= 500:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "server_error", "category": "technical",
                "severity": "critical", "impact_score": 95,
                "current_value": str(status),
                "fix_type": "manual",
            })
            continue
        if status in (401, 403):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "blocked_content", "category": "technical",
                "severity": "high", "impact_score": 70,
                "current_value": str(status),
                "fix_type": "manual",
            })

        title = page.get("title")
        title_len = page.get("title_length", 0)
        if not title:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_title", "category": "meta",
                "severity": "critical", "impact_score": 90,
                "current_value": None,
                "fix_type": "auto",
            })
        elif title_len < 30:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "title_too_short", "category": "meta",
                "severity": "high", "impact_score": 70,
                "current_value": title,
                "fix_type": "auto",
            })
        elif title_len > 60:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "title_too_long", "category": "meta",
                "severity": "medium", "impact_score": 50,
                "current_value": title,
                "fix_type": "auto",
            })

        desc = page.get("meta_description")
        desc_len = page.get("meta_description_length", 0)
        if not desc:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_meta_description", "category": "meta",
                "severity": "high", "impact_score": 80,
                "current_value": None,
                "fix_type": "auto",
            })
        elif desc_len > 160:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "meta_description_too_long", "category": "meta",
                "severity": "low", "impact_score": 30,
                "current_value": desc,
                "fix_type": "auto",
            })

        h1 = page.get("h1_count", 0)
        if h1 == 0:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_h1", "category": "headings",
                "severity": "high", "impact_score": 75,
                "current_value": None,
                "fix_type": "manual",
            })
        elif h1 > 1:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "multiple_h1", "category": "headings",
                "severity": "medium", "impact_score": 40,
                "current_value": str(h1),
                "fix_type": "manual",
            })

        # Gap 10: heading hierarchy skip
        skips = page.get("heading_hierarchy_skips") or []
        if skips:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "heading_hierarchy_skip", "category": "headings",
                "severity": "low", "impact_score": 20,
                "current_value": "; ".join(skips[:3]),
                "fix_type": "manual",
            })

        missing_alt = page.get("images_missing_alt", 0)
        if missing_alt > 0:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "images_missing_alt_text", "category": "images",
                "severity": "medium", "impact_score": 55,
                "current_value": str(missing_alt),
                "fix_type": "auto",
            })

        # Gap 11: non-modern image formats
        non_modern = page.get("images_non_modern_format", 0)
        if non_modern > 3:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "non_modern_image_format", "category": "performance",
                "severity": "medium", "impact_score": 45,
                "current_value": f"{non_modern} images not in WebP/AVIF",
                "fix_type": "manual",
            })

        if not page.get("schema_types"):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_schema", "category": "schema",
                "severity": "low", "impact_score": 25,
                "current_value": None,
                "fix_type": "manual",
            })

        if not (page.get("canonical_url") or page.get("http_canonical")):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_canonical", "category": "technical",
                "severity": "medium", "impact_score": 45,
                "current_value": None,
                "fix_type": "auto",
            })

        # Gap 9: page-type-aware thin content
        word_count = page.get("word_count", 0)
        threshold = THIN_CONTENT_THRESHOLDS.get(page_type, 250)
        if word_count < threshold:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "thin_content", "category": "content",
                "severity": "medium" if word_count < threshold // 2 else "low",
                "impact_score": 50 if word_count < threshold // 2 else 30,
                "current_value": f"{word_count} words ({page_type} threshold: {threshold})",
                "fix_type": "manual",
            })

        # Broken links count populated by orchestrator
        broken = page.get("broken_links_count", 0)
        if broken > 0:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "broken_links", "category": "technical",
                "severity": "high" if broken > 5 else "medium",
                "impact_score": min(40 + broken * 3, 80),
                "current_value": f"{broken} broken outbound links",
                "fix_type": "manual",
            })

    return issues
