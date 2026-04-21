"""AutoSEO AI Engine — Claude-powered SEO fix generation.

All methods in this module are fully implemented and ready to use.
They require the ANTHROPIC_API_KEY environment variable to be set.
When the key is not present, methods return structured placeholder responses
so the rest of the system can be developed and tested without API costs.
"""
from __future__ import annotations

import os
import json
import re
import logging
from typing import Optional
from dataclasses import dataclass, asdict

log = logging.getLogger(__name__)

# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class FixResult:
    fix: str
    confidence: float
    reasoning: str
    tier: int          # 1=auto-apply, 2=one-click, 3=manual
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class ContentBriefResult:
    title: str
    target_keyword: str
    outline: list[str]
    suggested_word_count: int
    tone: str
    notes: str


# ─── Pricing (as of Claude 3.5 / Sonnet 4.5) ─────────────────────────────────

PRICING = {
    "claude-haiku-3-5": {"input": 0.00025 / 1000, "output": 0.00125 / 1000},
    "claude-sonnet-4-5": {"input": 0.003 / 1000, "output": 0.015 / 1000},
}


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model, PRICING["claude-sonnet-4-5"])
    return round(input_tokens * p["input"] + output_tokens * p["output"], 6)


def _get_client():
    """Return Anthropic client or raise if key missing."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your environment secrets to enable AI features."
        )
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")


# ─── Fix Generation ───────────────────────────────────────────────────────────

# ─── Issue-specific prompt templates (Gap 21) ────────────────────────────────
# Generic prompts produce generic fixes. Each issue type gets its own template
# tuned to the constraints and writing style for that signal.

_GENERIC_PROMPT = """You are an expert SEO specialist. Generate a precise fix for this SEO issue.

ISSUE TYPE: {issue_type}
CURRENT VALUE: {current_value}
PAGE URL: {page_url}
PAGE TITLE: {page_title}
PAGE H1: {h1_text}
PAGE CONTENT EXCERPT: {content_excerpt}
TARGET KEYWORDS: {target_keywords}

CONSTRAINTS:
- Title tags: 30–60 characters, include primary keyword naturally
- Meta descriptions: 120–160 characters, include a compelling CTA
- Alt text: descriptive, under 125 characters
- H1: unique, descriptive, under 70 characters
- Output ONLY valid JSON — no markdown, no explanation.

Output format:
{{
  "fix": "<the exact replacement value>",
  "confidence": <0.0–1.0>,
  "reasoning": "<one sentence why this fix improves SEO>"
}}"""

ISSUE_PROMPTS: dict[str, str] = {
    "missing_meta_description": """You are an SEO copywriter. Write a meta description for this page.

URL: {page_url}
Page title: {page_title}
Main heading: {h1_text}
Page content (first 800 chars): {content_excerpt}
Target keywords: {target_keywords}

Rules:
- 130–155 characters EXACTLY
- Include the primary keyword naturally (do not stuff)
- Begin with a benefit-led hook
- Include one action verb (Discover, Learn, Get, See, Find, Compare)
- Do NOT use first person ("we", "our", "I")
- Do NOT mention the brand name (it's already in the title tag)
- Do NOT use superlatives ("best", "amazing", "ultimate")
- Plain text only — no quotes, no emoji

Output ONLY valid JSON:
{{"fix": "<meta description>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "title_too_short": """You are an SEO title-tag expert. Rewrite this title tag so it sits between 50 and 60 characters.

Current title: {current_value}
URL: {page_url}
H1: {h1_text}
Page excerpt: {content_excerpt}
Target keywords: {target_keywords}

Rules:
- 50–60 characters
- Lead with the primary keyword
- Add a specific qualifier (year, location, audience, format) when helpful
- Use sentence case or title case — match the site convention if visible in the excerpt
- No emoji, no ALL CAPS, no clickbait

Output ONLY valid JSON:
{{"fix": "<title>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "title_too_long": """You are an SEO title-tag expert. Shorten this title tag to fit within 60 characters without losing the primary keyword.

Current title: {current_value}
URL: {page_url}
Target keywords: {target_keywords}

Rules:
- 45–60 characters
- Keep the primary keyword
- Drop redundant brand suffixes if present
- No truncation with ellipses

Output ONLY valid JSON:
{{"fix": "<title>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "missing_title": """You are an SEO title-tag expert. Write a title tag for this page from scratch.

URL: {page_url}
Main heading: {h1_text}
Page excerpt: {content_excerpt}
Target keywords: {target_keywords}

Rules:
- 50–60 characters
- Include the primary keyword early
- Specific and unique to this page

Output ONLY valid JSON:
{{"fix": "<title>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "missing_h1": """You are an SEO content editor. Write the H1 for this page.

URL: {page_url}
Title: {page_title}
Page excerpt: {content_excerpt}
Target keywords: {target_keywords}

Rules:
- 30–70 characters
- Should communicate the page's primary purpose
- Include the primary keyword naturally
- Do not duplicate the title tag verbatim

Output ONLY valid JSON:
{{"fix": "<h1>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "images_missing_alt_text": """You are an accessibility & SEO specialist. Generate alt text suggestions.

Page title: {page_title}
URL: {page_url}
Context (first 500 chars): {content_excerpt}
Number of images missing alt: {current_value}

Rules:
- Each suggested alt text: 5–15 words
- Describe what would be visually in such an image given the page topic
- Include relevant keywords only when they fit naturally
- Do NOT begin with "Image of" or "Picture of"

Output ONLY valid JSON:
{{"fix": "<one example alt-text suggestion the user can adapt>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "missing_canonical": """You are a technical SEO. Suggest the canonical URL for this page.

URL: {page_url}

Rules:
- Use the absolute, lowercased, no-fragment, no-tracking-param version
- Use https when possible
- Strip trailing slash unless this is the root

Output ONLY valid JSON:
{{"fix": "<absolute canonical URL>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "missing_schema": """You are a structured-data expert. Suggest the JSON-LD schema type and minimal valid markup for this page.

URL: {page_url}
Title: {page_title}
H1: {h1_text}
Excerpt: {content_excerpt}

Rules:
- Pick the single MOST appropriate @type (Article, Product, FAQPage, Organization, WebPage, BreadcrumbList).
- Include @context, @type, and the truly required fields only.
- Use real values from the inputs above. Do not fabricate.
- Output the JSON-LD as a STRING inside the "fix" field.

Output ONLY valid JSON:
{{"fix": "<the full JSON-LD string>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",

    "meta_description_too_long": """You are an SEO copywriter. Tighten this meta description to fit within 155 characters without losing meaning.

Current: {current_value}
URL: {page_url}
Target keywords: {target_keywords}

Rules:
- 130–155 characters
- Keep the primary keyword and CTA
- No first person, no brand name, no superlatives

Output ONLY valid JSON:
{{"fix": "<meta description>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}""",
}


def _select_prompt(issue_type: str) -> str:
    return ISSUE_PROMPTS.get(issue_type, _GENERIC_PROMPT)


# Backwards-compat alias for any older callers
FIX_PROMPT = _GENERIC_PROMPT


def _determine_tier(issue_type: str, confidence: float) -> int:
    """Classify fix tier based on issue type and confidence score."""
    AUTO_TYPES = {"missing_alt_text", "missing_meta_description", "broken_canonical"}
    MANUAL_TYPES = {"content_rewrite", "structural_change", "duplicate_content"}

    if issue_type in MANUAL_TYPES:
        return 3
    if confidence >= 0.85 and issue_type in AUTO_TYPES:
        return 1
    return 2


def _use_haiku(issue_type: str) -> bool:
    """Use cheaper Haiku model for simple, templated fixes."""
    SIMPLE = {"missing_alt_text", "title_too_short", "title_too_long"}
    return issue_type in SIMPLE


async def generate_fix(
    issue_type: str,
    current_value: str,
    page_url: str,
    page_title: str = "",
    h1_text: str = "",
    content_excerpt: str = "",
    target_keywords: str = "",
) -> FixResult:
    """Generate an AI-powered SEO fix using Claude.

    Returns a stub response when ANTHROPIC_API_KEY is not set, allowing
    the full application to be used and tested without an API key.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set — returning stub fix for issue_type=%s", issue_type)
        return _stub_fix(issue_type, current_value)

    model = "claude-haiku-3-5" if _use_haiku(issue_type) else "claude-sonnet-4-5"

    template = _select_prompt(issue_type)
    prompt = template.format(
        issue_type=issue_type,
        current_value=current_value or "(empty)",
        page_url=page_url,
        page_title=page_title or "(unknown)",
        h1_text=h1_text or "(none)",
        content_excerpt=(content_excerpt or "")[:1000],
        target_keywords=target_keywords or "(none)",
    )

    try:
        client = _get_client()
        response = client.messages.create(
            model=model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)

        fix = data.get("fix", "")
        confidence = float(data.get("confidence", 0.7))
        reasoning = data.get("reasoning", "")
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return FixResult(
            fix=fix,
            confidence=confidence,
            reasoning=reasoning,
            tier=_determine_tier(issue_type, confidence),
            model_used=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_calc_cost(model, input_tokens, output_tokens),
        )

    except json.JSONDecodeError as exc:
        log.error("Claude returned non-JSON response: %s — %s", raw, exc)
        return _stub_fix(issue_type, current_value, error=str(exc))
    except Exception as exc:
        log.error("Claude API call failed: %s", exc)
        raise


def _stub_fix(issue_type: str, current_value: str, error: str = "") -> FixResult:
    """Return a clearly-labelled placeholder fix when API key is absent."""
    stubs: dict[str, str] = {
        "missing_meta_description": "Discover how AutoSEO automatically finds and fixes SEO issues on your website. Start your free trial today.",
        "missing_alt_text": "A descriptive image alt text would go here (AI key required for generation)",
        "title_too_long": (current_value or "Page title")[:57] if current_value else "Page Title — AutoSEO",
        "missing_h1": "Main Page Heading",
        "duplicate_title": f"Unique: {current_value[:45]}" if current_value else "Unique Page Title",
    }
    fix = stubs.get(issue_type, f"[AI fix for {issue_type} — ANTHROPIC_API_KEY required]")
    return FixResult(
        fix=fix,
        confidence=0.0,
        reasoning="Stub response — connect ANTHROPIC_API_KEY to enable real AI fixes",
        tier=2,
        model_used="none",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
    )


# ─── Content Brief ────────────────────────────────────────────────────────────

BRIEF_PROMPT = """You are a senior SEO content strategist. Create a content brief for the following target keyword.

TARGET KEYWORD: {keyword}
SITE DOMAIN: {domain}
COMPETITOR TITLES (for reference): {competitor_titles}

Generate a detailed content brief. Output ONLY valid JSON:
{{
  "title": "<SEO-optimised article title>",
  "target_keyword": "{keyword}",
  "outline": ["## Section 1", "## Section 2", "..."],
  "suggested_word_count": <number>,
  "tone": "<professional|conversational|authoritative>",
  "notes": "<2-3 sentences of key writing guidance>"
}}"""


async def generate_content_brief(
    keyword: str,
    domain: str = "",
    competitor_titles: list[str] | None = None,
) -> ContentBriefResult:
    """Generate a content brief for a target keyword using Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set — returning stub content brief")
        return ContentBriefResult(
            title=f"The Complete Guide to {keyword.title()}",
            target_keyword=keyword,
            outline=[
                "## Introduction",
                f"## What is {keyword.title()}?",
                "## Key Benefits",
                "## How to Get Started",
                "## Best Practices",
                "## Common Mistakes to Avoid",
                "## Conclusion",
            ],
            suggested_word_count=2000,
            tone="professional",
            notes="[Stub brief — connect ANTHROPIC_API_KEY to generate real content briefs]",
        )

    try:
        client = _get_client()
        prompt = BRIEF_PROMPT.format(
            keyword=keyword,
            domain=domain or "your site",
            competitor_titles=json.dumps(competitor_titles or []),
        )
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return ContentBriefResult(**data)
    except Exception as exc:
        log.error("Content brief generation failed: %s", exc)
        raise


# ─── Bulk Fix Generation ──────────────────────────────────────────────────────

async def generate_fixes_bulk(issues: list[dict]) -> list[FixResult]:
    """Generate fixes for a list of issues. Processes concurrently."""
    import asyncio
    tasks = [
        generate_fix(
            issue_type=i.get("type", ""),
            current_value=i.get("current_value", ""),
            page_url=i.get("page_url", ""),
            page_title=i.get("page_title", ""),
            h1_text=i.get("h1_text", ""),
            content_excerpt=i.get("content_excerpt", ""),
            target_keywords=i.get("target_keywords", ""),
        )
        for i in issues
    ]
    return await asyncio.gather(*tasks)
