"""Safety validation for AI-generated repository file changes."""
from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from typing import Any


ALLOWED_EXTENSIONS = {
    ".astro",
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mdx",
    ".mjs",
    ".mts",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
}

FORBIDDEN_EXACT = {
    ".env",
    ".env.local",
    ".env.production",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
}

FORBIDDEN_PARTS = {
    ".git",
    ".github/workflows",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
}

SECRET_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "SUPABASE_SERVICE_ROLE_KEY",
    "STRIPE_SECRET_KEY",
)


@dataclass
class PatchSafetyResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    sanitized_changes: list[dict[str, Any]]


def _extension(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    if name in {"robots.txt", "sitemap.xml"}:
        return "." + name.rsplit(".", 1)[-1]
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1].lower()


def _normalize_path(path: str, project_root: str = "") -> tuple[str | None, str | None]:
    raw = (path or "").replace("\\", "/").strip().lstrip("/")
    root = (project_root or "").replace("\\", "/").strip().strip("/")
    if not raw:
        return None, "Missing file path"
    if raw.startswith("../") or "/../" in raw or raw == "..":
        return None, f"Path escapes project root: {path}"
    normalized = posixpath.normpath(raw)
    if normalized == "." or normalized.startswith("../"):
        return None, f"Path escapes project root: {path}"
    if root and not (normalized == root or normalized.startswith(f"{root}/")):
        normalized = f"{root}/{normalized}"
    return normalized, None


def validate_file_changes(
    changes: list[dict[str, Any]] | None,
    *,
    project_root: str = "",
    max_files: int = 6,
    max_file_chars: int = 70000,
    max_total_chars: int = 180000,
) -> PatchSafetyResult:
    errors: list[str] = []
    warnings: list[str] = []
    sanitized: list[dict[str, Any]] = []
    total_chars = 0

    if not changes:
        return PatchSafetyResult(False, ["No file changes were proposed"], [], [])
    if len(changes) > max_files:
        errors.append(f"Too many files changed: {len(changes)} proposed, max {max_files}")

    seen: set[str] = set()
    for index, change in enumerate(changes[:max_files], start=1):
        normalized, path_error = _normalize_path(str(change.get("path") or ""), project_root)
        if path_error:
            errors.append(path_error)
            continue
        assert normalized is not None
        if normalized in seen:
            errors.append(f"Duplicate file change: {normalized}")
            continue
        seen.add(normalized)

        action = str(change.get("action") or "update").lower()
        if action not in {"create", "update"}:
            errors.append(f"{normalized}: unsupported action {action}")

        base_name = normalized.rsplit("/", 1)[-1]
        if base_name in FORBIDDEN_EXACT:
            errors.append(f"{normalized}: protected file cannot be changed")
        if any(normalized == part or normalized.startswith(f"{part}/") or f"/{part}/" in normalized for part in FORBIDDEN_PARTS):
            errors.append(f"{normalized}: protected directory cannot be changed")
        ext = _extension(normalized)
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{normalized}: extension {ext or '(none)'} is not allowed for AI patches")

        content = change.get("content")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"{normalized}: full replacement content is required")
            content = ""
        if "\x00" in content:
            errors.append(f"{normalized}: binary-looking content rejected")
        if len(content) > max_file_chars:
            errors.append(f"{normalized}: file content exceeds {max_file_chars} characters")
        if any(marker in content for marker in SECRET_MARKERS):
            errors.append(f"{normalized}: content includes secret-looking marker")
        if re.search(r"(sk-ant-|ghp_|github_pat_|xox[baprs]-)", content):
            errors.append(f"{normalized}: content includes token-looking value")

        total_chars += len(content)
        sanitized.append(
            {
                "path": normalized,
                "action": action,
                "summary": str(change.get("summary") or f"Update {normalized}")[:500],
                "content": content,
            }
        )

    if total_chars > max_total_chars:
        errors.append(f"Patch is too large: {total_chars} characters, max {max_total_chars}")
    if not errors and total_chars > 100000:
        warnings.append("Large patch; create a draft PR and review carefully.")

    return PatchSafetyResult(not errors, errors, warnings, sanitized)
