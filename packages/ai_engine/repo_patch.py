"""AI planner for repository-level SEO fixes."""
from __future__ import annotations

import json
import re
from typing import Any

from packages.ai_engine.engine import AIProviderUnavailable, _get_client, is_ai_configured
from packages.shared.patch_safety import validate_file_changes


SUPPORTED_AI_PATCH_ISSUES = {
    "duplicate_title",
    "stale_schema_date",
    "unverified_review_schema",
    "missing_offer_schema",
    "broken_og_image",
    "spa_no_prerender",
}


def ai_patch_supported(issue_type: str) -> bool:
    return issue_type in SUPPORTED_AI_PATCH_ISSUES


def _strip_json_fence(raw: str) -> str:
    return re.sub(r"^```json\s*|```$", "", raw.strip(), flags=re.MULTILINE).strip()


def _compact_file_context(files: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    total = 0
    for item in files[:8]:
        content = str(item.get("content") or "")
        if not content:
            continue
        snippet = content[:18000]
        total += len(snippet)
        if total > 90000:
            break
        chunks.append(
            f"\n--- FILE: {item.get('path')} ---\n"
            f"{snippet}\n"
            f"--- END FILE: {item.get('path')} ---"
        )
    return "\n".join(chunks)


def build_plan_only_preview(
    *,
    issue_type: str,
    title: str,
    affected_urls: list[str],
    manual_steps: list[str],
    repo_analysis: dict,
    reason: str,
) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "summary": title,
        "risk_level": "high",
        "mode": "plan_only",
        "ai_model": None,
        "affected_urls": affected_urls[:25],
        "files_to_inspect": repo_analysis.get("files_found", []),
        "proposed_files_to_change": [],
        "missing_user_data": [],
        "patch_summary": reason,
        "review_notes": manual_steps,
        "file_changes": [],
        "safety": {
            "ok": True,
            "errors": [],
            "warnings": ["Plan-only PR: no source code will be modified automatically."],
        },
    }


async def generate_repo_patch_preview(
    *,
    issue_type: str,
    title: str,
    summary: str,
    recommended_fix: str,
    site_domain: str,
    affected_urls: list[str],
    examples: list[dict[str, Any]],
    manual_steps: list[str],
    repo_analysis: dict,
    file_contexts: list[dict[str, Any]],
    project_root: str = "",
    business_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ask Claude for a structured, safety-checkable repo patch preview."""
    if not is_ai_configured():
        raise AIProviderUnavailable("ANTHROPIC_API_KEY is not set")
    if issue_type not in SUPPORTED_AI_PATCH_ISSUES:
        return build_plan_only_preview(
            issue_type=issue_type,
            title=title,
            affected_urls=affected_urls,
            manual_steps=manual_steps,
            repo_analysis=repo_analysis,
            reason="This issue type is not yet supported for AI code patching.",
        )

    file_context = _compact_file_context(file_contexts)
    prompt = f"""You are AutoSEO's repository patch planner. Create a safe SEO code patch.

Return ONLY valid JSON. Do not include markdown fences.

Issue:
- type: {issue_type}
- title: {title}
- summary: {summary}
- recommended fix: {recommended_fix}
- site: {site_domain}
- affected URLs: {json.dumps(affected_urls[:30])}
- examples: {json.dumps(examples[:10])}
- manual recipe: {json.dumps(manual_steps)}

Repository:
{json.dumps(repo_analysis)}

User business context:
{json.dumps(business_context or {})}

Rules:
- Change at most 5 files.
- Only propose full replacement content for files shown below.
- If you need a new file, keep it under the selected project root/public or project root/src.
- Do not modify .env, lockfiles, CI workflows, secrets, package manager lockfiles, or generated build output.
- Do not fabricate reviews, ratings, prices, dates, or offers. If business context is missing, put it in missing_user_data and do not patch that claim.
- For spa_no_prerender, prefer plan_only unless the repository clearly supports a safe framework-level metadata/prerender change.
- Output full replacement content for every file change.

Output JSON shape:
{{
  "issue_type": "{issue_type}",
  "summary": "one sentence",
  "risk_level": "low|medium|high",
  "mode": "file_patch|plan_only",
  "files_to_inspect": ["path"],
  "proposed_files_to_change": ["path"],
  "missing_user_data": ["item"],
  "patch_summary": "short human summary",
  "review_notes": ["note"],
  "file_changes": [
    {{"path": "relative/path", "action": "update|create", "summary": "what changed", "content": "full replacement file content"}}
  ]
}}

Available file contents:
{file_context}
"""

    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=12000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
    data = json.loads(_strip_json_fence(raw))

    file_changes = data.get("file_changes") or []
    if data.get("mode") == "plan_only":
        file_changes = []
    safety = validate_file_changes(file_changes, project_root=project_root) if file_changes else None

    return {
        "issue_type": issue_type,
        "summary": str(data.get("summary") or title),
        "risk_level": str(data.get("risk_level") or "high"),
        "mode": "file_patch" if file_changes else "plan_only",
        "ai_model": "claude-sonnet-4-5",
        "affected_urls": affected_urls[:25],
        "files_to_inspect": data.get("files_to_inspect") or [item.get("path") for item in file_contexts],
        "proposed_files_to_change": data.get("proposed_files_to_change") or [item.get("path") for item in file_changes],
        "missing_user_data": data.get("missing_user_data") or [],
        "patch_summary": str(data.get("patch_summary") or ""),
        "review_notes": data.get("review_notes") or [],
        "file_changes": safety.sanitized_changes if safety else [],
        "safety": {
            "ok": safety.ok if safety else True,
            "errors": safety.errors if safety else [],
            "warnings": safety.warnings if safety else ["Plan-only preview: no source code changes proposed."],
        },
        "token_usage": {
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
        },
    }
