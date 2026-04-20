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

FIX_PROMPT = """You are an expert SEO specialist. Generate a precise fix for this SEO issue.

ISSUE TYPE: {issue_type}
CURRENT VALUE: {current_value}
PAGE URL: {page_url}
PAGE TITLE: {page_title}
PAGE H1: {h1_text}
PAGE CONTENT EXCERPT: {content_excerpt}
TARGET KEYWORDS: {target_keywords}

CONSTRAINTS:
- Title tags: 30–60 characters, include primary keyword naturally
- Meta descriptions: 120–160 characters, include a compelling call to action
- Alt text: descriptive, keyword-relevant, under 125 characters
- H1: unique, descriptive, includes primary keyword, under 70 characters
- Output ONLY valid JSON — no markdown, no explanation

Output format:
{{
  "fix": "<the exact replacement value>",
  "confidence": <0.0–1.0>,
  "reasoning": "<one sentence why this fix improves SEO>"
}}"""


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

    prompt = FIX_PROMPT.format(
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
