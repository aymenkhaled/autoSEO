"""AI safety utilities — input sanitization & output validation.

Hardens the AI fix pipeline against:
  • Prompt injection via crafted HTML sent to Claude
  • Malicious AI output (script/event handlers/javascript: URLs) being
    written back into a customer CMS

Used by packages.ai_engine.engine and any worker that ships AI output
to a write surface.
"""
from __future__ import annotations

import re
from html import unescape

# ── Input sanitization ──────────────────────────────────────────────────────

_TAG_BLOCK = re.compile(r"<(script|style|iframe|object|embed|noscript)\b[\s\S]*?</\1>", re.I)
_HTML_COMMENT = re.compile(r"<!--[\s\S]*?-->")
_EVENT_ATTR = re.compile(r"\son\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
_DATA_URL = re.compile(r"data:[^\s\"'<>]+", re.I)
_JS_URL = re.compile(r"javascript:[^\s\"'<>]+", re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# Phrases that have been observed in real-world prompt-injection payloads.
# These get neutralized (collapsed) rather than removed to keep length stable.
_INJECTION_PATTERNS = [
    re.compile(r"ignore (?:all )?(?:previous|prior|above) instructions?", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"you are now [a-z ]+", re.I),
    re.compile(r"reveal (?:your )?(?:system )?prompt", re.I),
    re.compile(r"```[a-z]*\s*system", re.I),
]


def sanitize_html_for_ai(html: str, max_len: int = 1500) -> str:
    """Strip dangerous markup and obvious injection vectors from HTML
    before sending it to an LLM as context.

    Returns plain-ish text safe to embed in a prompt.
    """
    if not html:
        return ""
    text = _HTML_COMMENT.sub(" ", html)
    text = _TAG_BLOCK.sub(" ", text)
    text = _EVENT_ATTR.sub(" ", text)
    text = _JS_URL.sub("[blocked-js-url]", text)
    text = _DATA_URL.sub("[blocked-data-url]", text)
    text = _TAG.sub(" ", text)
    text = unescape(text)
    for pat in _INJECTION_PATTERNS:
        text = pat.sub("[redacted]", text)
    text = _WS.sub(" ", text).strip()
    return text[:max_len]


def sanitize_field_value(value: str | None, max_len: int = 1000) -> str:
    """Sanitize a single field value (title/meta/h1) before it is shown
    in a prompt — strip tags & collapse whitespace, never silently mutate
    semantic content.
    """
    if not value:
        return ""
    text = _TAG.sub(" ", value)
    text = unescape(text)
    text = _WS.sub(" ", text).strip()
    for pat in _INJECTION_PATTERNS:
        text = pat.sub("[redacted]", text)
    return text[:max_len]


# ── Output validation ──────────────────────────────────────────────────────

_OUTPUT_DANGEROUS = re.compile(
    r"<\s*script\b|<\s*iframe\b|on\w+\s*=|javascript:|data:text/html|<!--",
    re.I,
)


class UnsafeAIOutput(ValueError):
    """Raised when an AI-generated fix would be dangerous to write to a CMS."""


def validate_ai_output(value: str, *, field: str) -> str:
    """Reject AI fix output that contains dangerous markup.

    `field` controls leniency:
      • `schema` — JSON-LD; allow more characters but still no <script src=>
      • everything else — text fields, must be plain
    """
    if value is None:
        raise UnsafeAIOutput("AI output was empty")
    text = str(value).strip()
    if not text:
        raise UnsafeAIOutput("AI output was empty")

    if field == "schema":
        # JSON-LD: must be embeddable in a <script type="application/ld+json">
        # Block any nested </script> closer to prevent breakout.
        if "</script" in text.lower():
            raise UnsafeAIOutput("Schema fix contains </script> closer")
        return text

    if _OUTPUT_DANGEROUS.search(text):
        raise UnsafeAIOutput(
            f"AI output for field '{field}' contains disallowed markup "
            "(script/iframe/event handler/javascript: URL)"
        )
    return text
