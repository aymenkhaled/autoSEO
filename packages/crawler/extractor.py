"""SEO signal extractor — parses HTML and extracts all spec-defined signals."""
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse


class SEOExtractor:
    def __init__(self, html: str, url: str):
        self.soup = BeautifulSoup(html, "lxml")
        self.url = url
        self.base_domain = urlparse(url).netloc

    def extract_all(self) -> dict:
        return {
            **self._meta(),
            **self._headings(),
            **self._links(),
            **self._images(),
            **self._schema(),
            **self._social(),
            **self._technical(),
        }

    def _meta(self) -> dict:
        title_tag = self.soup.find("title")
        desc_tag = self.soup.find("meta", attrs={"name": "description"})
        canonical_tag = self.soup.find("link", attrs={"rel": "canonical"})
        robots_tag = self.soup.find("meta", attrs={"name": "robots"})
        viewport_tag = self.soup.find("meta", attrs={"name": "viewport"})
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
        }

    def _headings(self) -> dict:
        h1s = self.soup.find_all("h1")
        h2s = self.soup.find_all("h2")
        h3s = self.soup.find_all("h3")
        structure = []
        for tag in self.soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            structure.append({"level": int(tag.name[1]), "text": tag.get_text(strip=True)[:200]})
        return {
            "h1_count": len(h1s),
            "h1_text": [h.get_text(strip=True) for h in h1s],
            "h2_count": len(h2s),
            "h3_count": len(h3s),
            "heading_structure": structure[:50],
        }

    def _links(self) -> dict:
        links = self.soup.find_all("a", href=True)
        internal = []
        external = []
        for l in links:
            href = l.get("href", "")
            parsed = urlparse(href)
            if parsed.netloc in ("", self.base_domain):
                internal.append(href)
            elif parsed.scheme in ("http", "https"):
                external.append(href)
        return {
            "internal_links_count": len(internal),
            "external_links_count": len(external),
            "broken_links_count": 0,
        }

    def _images(self) -> dict:
        imgs = self.soup.find_all("img")
        missing_alt = sum(1 for i in imgs if not i.get("alt", "").strip())
        return {
            "images_count": len(imgs),
            "images_missing_alt": missing_alt,
            "images_large": 0,
        }

    def _schema(self) -> dict:
        schemas, types, errors = [], [], []
        for s in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "")
                schemas.append(data)
                if isinstance(data, dict) and "@type" in data:
                    types.append(data["@type"])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "@type" in item:
                            types.append(item["@type"])
            except (json.JSONDecodeError, ValueError) as e:
                errors.append(str(e))
        return {
            "schema_types": types,
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
        words = [w for w in text.split() if len(w) > 1]
        return {
            "hreflang_tags": hreflang if hreflang else None,
            "hreflang_errors": [],
            "word_count": len(words),
        }


def calculate_page_score(signals: dict) -> int:
    """Weighted SEO score 0–100 based on extracted signals."""
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

    if signals.get("images_missing_alt", 0) > 0:
        ratio = min(signals["images_missing_alt"] / max(signals.get("images_count", 1), 1), 1.0)
        deductions.append(int(ratio * 10))

    if not signals.get("schema_types"):
        deductions.append(5)

    if not signals.get("canonical_url"):
        deductions.append(5)

    if signals.get("word_count", 0) < 300:
        deductions.append(5)

    return max(0, score - sum(deductions))


def generate_issues(pages: list[dict]) -> list[dict]:
    """Generate issue records from extracted page signals."""
    issues = []
    for page in pages:
        url = page.get("url", "")
        page_id = page.get("_page_id")

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

        missing_alt = page.get("images_missing_alt", 0)
        if missing_alt > 0:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "images_missing_alt_text", "category": "images",
                "severity": "medium", "impact_score": 55,
                "current_value": str(missing_alt),
                "fix_type": "auto",
            })

        if not page.get("schema_types"):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_schema", "category": "schema",
                "severity": "low", "impact_score": 25,
                "current_value": None,
                "fix_type": "manual",
            })

        if not page.get("canonical_url"):
            issues.append({
                "page_id": page_id, "url": url,
                "type": "missing_canonical", "category": "technical",
                "severity": "medium", "impact_score": 45,
                "current_value": None,
                "fix_type": "auto",
            })

        word_count = page.get("word_count", 0)
        if word_count < 300:
            issues.append({
                "page_id": page_id, "url": url,
                "type": "thin_content", "category": "content",
                "severity": "medium", "impact_score": 50,
                "current_value": str(word_count),
                "fix_type": "manual",
            })

    return issues
