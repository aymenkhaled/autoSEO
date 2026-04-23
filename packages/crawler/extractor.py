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
from collections import defaultdict
from datetime import date, datetime
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
        signals = {
            **self._meta(),
            **self._headings(),
            **self._links(),
            **self._images(),
            **self._schema(),
            **self._social(),
            **self._technical(),
            **self._http_headers(),
        }
        signals["is_spa_shell"] = self._detect_spa_shell(signals)
        return signals

    def _detect_spa_shell(self, signals: dict) -> bool:
        """Detect an unrendered client-side SPA (React/Vue/Next/Angular).

        Other agent's feedback: 'crawler sees empty <div id="root">' on SPAs.
        When this is true, downstream missing-h1/thin-content issues are
        symptoms of one root cause, not 17 separate problems.
        """
        body = self.soup.find("body")
        if not body:
            return False
        # Look for framework root markers
        markers = (
            ("div", {"id": "root"}),
            ("div", {"id": "app"}),
            ("div", {"id": "__next"}),
            ("div", {"id": "__nuxt"}),
            ("div", {"data-reactroot": True}),
        )
        has_marker = any(self.soup.find(tag, attrs) for tag, attrs in markers)
        if not has_marker:
            # Also catch generic ng-app or vue-style roots
            has_marker = bool(self.soup.find(attrs={"ng-app": True})) or "data-v-app" in str(body)[:2000]

        word_count = signals.get("word_count", 0)
        h1_count = signals.get("h1_count", 0)
        # Shell heuristic: framework marker + almost no rendered content
        return bool(has_marker and word_count < 50 and h1_count == 0)

    def _meta(self) -> dict:
        title_tag = self.soup.find("title")
        desc_tag = self.soup.find("meta", attrs={"name": "description"})
        canonical_tag = self.soup.find("link", attrs={"rel": "canonical"})
        robots_tag = self.soup.find("meta", attrs={"name": "robots"})
        viewport_tag = self.soup.find("meta", attrs={"name": "viewport"})
        # Charset: <meta charset=…> OR <meta http-equiv="content-type">
        charset_tag = self.soup.find("meta", attrs={"charset": True})
        if not charset_tag:
            ct_tag = self.soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "content-type"})
            charset_tag = ct_tag if ct_tag and "charset" in (ct_tag.get("content") or "").lower() else None
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
            "has_charset": charset_tag is not None,
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

        # Detect stale offer dates (priceValidUntil in the past)
        stale_dates: list[str] = []
        for d in schemas:
            stale_dates.extend(_find_stale_offer_dates(d))

        page_text = self.soup.get_text(" ", strip=True)
        return {
            "schema_jsonld": schemas,
            "schema_types": [str(t) for t in types],
            "schema_valid": len(errors) == 0,
            "schema_errors": errors if errors else None,
            "stale_offer_dates": stale_dates if stale_dates else None,
            "review_schema_risks": _find_review_policy_risks(schemas) or None,
            "missing_visible_offer_schema": _detect_missing_visible_offer_schema(schemas, page_text),
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

        # Bug 2: content fingerprint for near-duplicate detection.
        # Lightweight SimHash-style normalization: lowercase + collapse whitespace,
        # then SHA-1. Pages with identical normalized body text will collide,
        # which catches the common WP/Shopify duplicate-content patterns.
        import hashlib
        normalized = " ".join(w.lower() for w in words)
        content_hash = hashlib.sha1(normalized.encode("utf-8")).hexdigest() if normalized else None

        # Mixed content: count http:// references inside an https page
        mixed_count = 0
        if self.url.startswith("https://"):
            for tag, attr in (("img", "src"), ("script", "src"), ("link", "href"),
                              ("iframe", "src"), ("source", "src"), ("video", "src")):
                for el in self.soup.find_all(tag):
                    val = (el.get(attr) or "").strip()
                    if val.startswith("http://"):
                        mixed_count += 1

        return {
            "hreflang_tags": hreflang if hreflang else None,
            "hreflang_errors": [],
            "word_count": len(words),
            "content_hash": content_hash,
            "mixed_content": mixed_count,
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


def _find_stale_offer_dates(node, found: list[str] | None = None) -> list[str]:
    """Walk a JSON-LD tree looking for past priceValidUntil/validThrough dates."""
    if found is None:
        found = []
    today = date.today()
    if isinstance(node, dict):
        for key in ("priceValidUntil", "validThrough", "validUntil"):
            v = node.get(key)
            if isinstance(v, str):
                # Try ISO 8601 (YYYY-MM-DD or full datetime)
                try:
                    parsed = datetime.fromisoformat(v.replace("Z", "+00:00")).date()
                except ValueError:
                    try:
                        parsed = datetime.strptime(v[:10], "%Y-%m-%d").date()
                    except ValueError:
                        continue
                if parsed < today:
                    found.append(f"{key}={v}")
        for v in node.values():
            _find_stale_offer_dates(v, found)
    elif isinstance(node, list):
        for v in node:
            _find_stale_offer_dates(v, found)
    return found


def _iter_schema_nodes(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _iter_schema_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_schema_nodes(value)


def _find_review_policy_risks(schemas: list) -> list[str]:
    """Flag review/rating claims that need proof before Google can trust them."""
    risks: list[str] = []
    for schema in schemas:
        for node in _iter_schema_nodes(schema):
            if not isinstance(node, dict):
                continue
            aggregate = node.get("aggregateRating")
            reviews = node.get("review") or node.get("reviews")
            if aggregate:
                rating = aggregate.get("ratingValue") if isinstance(aggregate, dict) else aggregate
                count = aggregate.get("reviewCount") if isinstance(aggregate, dict) else None
                risks.append(f"aggregateRating rating={rating} reviewCount={count}")
            if reviews:
                review_list = reviews if isinstance(reviews, list) else [reviews]
                names: list[str] = []
                for review in review_list[:5]:
                    if not isinstance(review, dict):
                        continue
                    author = review.get("author")
                    name = author.get("name") if isinstance(author, dict) else author
                    if name:
                        names.append(str(name))
                risks.append(
                    "Review markup includes named reviews"
                    + (f": {', '.join(names[:3])}" if names else "")
                )
    return list(dict.fromkeys(risks))


def _detect_missing_visible_offer_schema(schemas: list, page_text: str) -> bool:
    text = (page_text or "").lower()
    has_lifetime_offer = "lifetime" in text and ("$499" in text or "499" in text)
    if not has_lifetime_offer:
        return False

    has_offer_schema = False
    has_499_offer = False
    for schema in schemas:
        for node in _iter_schema_nodes(schema):
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("@type", "")).lower()
            if "offer" in node_type or "price" in node or "offers" in node:
                has_offer_schema = True
                packed = json.dumps(node, default=str).lower()
                if "499" in packed or "lifetime" in packed:
                    has_499_offer = True
    return has_offer_schema and not has_499_offer


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
    """Additive SEO score 0–100.

    Awards points for positive signals rather than starting at 100 and deducting.
    This means an empty/skeleton page legitimately scores low (it has nothing
    going for it) instead of artificially landing in the 60s after deductions.
    """
    status = signals.get("status_code", 200) or 200
    if status in (404, 410):
        return 0
    if status >= 500:
        return 5

    score = 0
    page_type = signals.get("page_type") or "generic"

    # Title (max 18 pts)
    title = signals.get("title")
    title_len = signals.get("title_length", 0)
    if title:
        score += 8
        if 30 <= title_len <= 60:
            score += 10
        elif 20 <= title_len <= 70:
            score += 5

    # Meta description (max 14 pts)
    desc = signals.get("meta_description")
    desc_len = signals.get("meta_description_length", 0)
    if desc:
        score += 6
        if 120 <= desc_len <= 160:
            score += 8
        elif 70 <= desc_len <= 180:
            score += 4

    # H1 (max 10 pts)
    h1_count = signals.get("h1_count", 0)
    if h1_count == 1:
        score += 10
    elif h1_count > 1:
        score += 4

    # Heading hierarchy intact (5 pts)
    if h1_count >= 1 and not signals.get("heading_hierarchy_skips"):
        score += 5

    # Images (max 8 pts)
    img_total = signals.get("images_count", 0) or 0
    img_missing = signals.get("images_missing_alt", 0) or 0
    if img_total == 0:
        score += 4  # neutral — no images, no problem
    else:
        coverage = max(0.0, 1.0 - (img_missing / img_total))
        score += int(8 * coverage)

    # Modern formats (3 pts) — credit if there are images and most are modern
    if img_total > 0 and signals.get("images_non_modern_format", 0) <= max(2, img_total // 5):
        score += 3

    # Canonical (6 pts)
    if signals.get("canonical_url") or signals.get("http_canonical"):
        score += 6

    # Structured data (8 pts)
    if signals.get("schema_types"):
        score += 6
        if signals.get("schema_valid", True):
            score += 2

    # Open graph / social (5 pts)
    if signals.get("og_title") and signals.get("og_description"):
        score += 5

    # Mobile viewport (4 pts)
    if signals.get("has_viewport"):
        score += 4

    # Charset declared (2 pts)
    if signals.get("has_charset"):
        score += 2

    # HTTPS / no mixed content (4 pts)
    if signals.get("url", "").startswith("https://") and not signals.get("mixed_content"):
        score += 4

    # Content depth (max 13 pts) — page-type aware
    word_count = signals.get("word_count", 0) or 0
    threshold = THIN_CONTENT_THRESHOLDS.get(page_type, 250)
    if word_count >= threshold * 2:
        score += 13
    elif word_count >= threshold:
        score += 9
    elif word_count >= threshold // 2:
        score += 4

    return max(0, min(100, score))


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
        is_shell = page.get("is_spa_shell", False)

        # SPA shell: emit ONE root-cause issue and skip the symptoms (missing h1,
        # thin content, missing meta) since they're all caused by the same thing.
        if is_shell:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "spa_no_prerender", "category": "rendering",
                "severity": "critical", "impact_score": 95,
                "current_value": "Page is a client-rendered SPA shell — crawlers see empty HTML",
                "fix_type": "manual",
            })
            # Stale offer dates can still be detected (they're in raw HTML), continue with those only
            for stale in (page.get("stale_offer_dates") or []):
                issues.append({
                    "page_id": page_id, "url": url,
                    "type": "stale_schema_date", "category": "schema",
                    "severity": "medium", "impact_score": 40,
                    "current_value": stale,
                    "fix_type": "auto",
                })
            for risk in (page.get("review_schema_risks") or []):
                issues.append({
                    "page_id": page_id, "url": url,
                    "type": "unverified_review_schema", "category": "schema",
                    "severity": "high", "impact_score": 70,
                    "current_value": risk,
                    "fix_type": "manual",
                })
            if page.get("missing_visible_offer_schema"):
                issues.append({
                    "page_id": page_id, "url": url,
                    "type": "missing_offer_schema", "category": "schema",
                    "severity": "medium", "impact_score": 45,
                    "current_value": "Visible lifetime/$499 offer is not represented in JSON-LD offers",
                    "fix_type": "auto",
                })
            if page.get("og_image_valid") is False:
                issues.append({
                    "page_id": page_id, "url": url,
                    "type": "broken_og_image", "category": "social",
                    "severity": "medium", "impact_score": 45,
                    "current_value": page.get("og_image") or "og:image missing or unreachable",
                    "fix_type": "manual",
                })
            continue

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

        # Mobile viewport
        if not page.get("has_viewport"):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_viewport", "category": "mobile",
                "severity": "high", "impact_score": 65,
                "current_value": "No <meta name='viewport'> tag",
                "fix_type": "manual",
            })

        # Charset declaration
        if not page.get("has_charset"):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_charset", "category": "technical",
                "severity": "low", "impact_score": 20,
                "current_value": "No <meta charset> declared",
                "fix_type": "manual",
            })

        # Mixed content (https page loading http:// resources)
        mixed = page.get("mixed_content") or 0
        if mixed > 0:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "mixed_content", "category": "security",
                "severity": "high" if mixed > 3 else "medium",
                "impact_score": min(50 + mixed * 5, 85),
                "current_value": f"{mixed} insecure http:// resources on https page",
                "fix_type": "manual",
            })

        # Stale offer dates from JSON-LD
        for stale in (page.get("stale_offer_dates") or []):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "stale_schema_date", "category": "schema",
                "severity": "medium", "impact_score": 40,
                "current_value": stale,
                "fix_type": "auto",
            })

        for risk in (page.get("review_schema_risks") or []):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "unverified_review_schema", "category": "schema",
                "severity": "high", "impact_score": 70,
                "current_value": risk,
                "fix_type": "manual",
            })

        if page.get("missing_visible_offer_schema"):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_offer_schema", "category": "schema",
                "severity": "medium", "impact_score": 45,
                "current_value": "Visible lifetime/$499 offer is not represented in JSON-LD offers",
                "fix_type": "auto",
            })

        if page.get("og_image_valid") is False:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "broken_og_image", "category": "social",
                "severity": "medium", "impact_score": 45,
                "current_value": page.get("og_image") or "og:image missing or unreachable",
                "fix_type": "manual",
            })

    # Site-wide aggregate detection: dedupe symptoms into one root-cause issue
    issues.extend(detect_sitewide_duplicates(pages))

    return issues


def detect_sitewide_duplicates(pages: list[dict]) -> list[dict]:
    """Aggregate identical titles / meta descriptions across pages.

    The other agent's feedback: 'every single page on your site uses the exact
    same title' — that should surface as ONE high-impact issue with the list of
    affected URLs, not 17 separate copies of `title_too_long`.
    """
    aggregate: list[dict] = []

    # Group by normalized title
    by_title: dict[str, list[dict]] = defaultdict(list)
    by_meta: dict[str, list[dict]] = defaultdict(list)
    for p in pages:
        t = (p.get("title") or "").strip().lower()
        if t:
            by_title[t].append(p)
        m = (p.get("meta_description") or "").strip().lower()
        if m:
            by_meta[m].append(p)

    for title, group in by_title.items():
        if len(group) >= 2:
            urls = [g.get("url", "") for g in group]
            aggregate.append({
                "page_id": group[0].get("_page_id"),
                "url": group[0].get("url", ""),
                "type": "duplicate_title",
                "category": "meta",
                "severity": "high" if len(group) >= 5 else "medium",
                "impact_score": min(60 + len(group) * 2, 90),
                "current_value": f"{len(group)} pages share this title: {title[:80]}",
                "fix_type": "manual",
                "_affected_urls": urls,
            })

    for meta, group in by_meta.items():
        if len(group) >= 2:
            urls = [g.get("url", "") for g in group]
            aggregate.append({
                "page_id": group[0].get("_page_id"),
                "url": group[0].get("url", ""),
                "type": "duplicate_meta_description",
                "category": "meta",
                "severity": "medium",
                "impact_score": min(40 + len(group) * 2, 70),
                "current_value": f"{len(group)} pages share this meta description",
                "fix_type": "manual",
                "_affected_urls": urls,
            })

    return aggregate
