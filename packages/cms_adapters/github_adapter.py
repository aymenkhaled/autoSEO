"""GitHub CMS Adapter — applies SEO fixes via Pull Requests.

Supports static site generators: Next.js, Astro, Hugo, Jekyll.

Flow:
1. User installs the AutoSEO GitHub App on their repo
2. We detect the site framework from repo structure
3. For each fix: create a branch → commit the change → open a PR
4. User reviews and merges the PR (no auto-merge without explicit consent)

Requires:
    GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY environment variables,
    OR a personal access token with repo write scope.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Optional

import httpx

from .base import BaseCMSAdapter, CMSPage, ApplyResult

log = logging.getLogger(__name__)

GH_API = "https://api.github.com"


class GitHubAdapter(BaseCMSAdapter):
    """GitHub adapter — creates fix PRs instead of direct writes.

    Args:
        owner: GitHub org or username
        repo: Repository name
        token: GitHub personal access token or installation token
        branch: Default branch (default: main)
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        branch: str = "main",
    ):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.branch = branch
        self._framework: Optional[str] = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def test_connection(self) -> bool:
        """Verify token with a read-only repo access check."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}",
                headers=self._headers(),
            )
            return resp.status_code == 200

    async def _detect_framework(self, client: httpx.AsyncClient) -> str:
        """Detect static site framework from repo root."""
        markers = {
            "astro.config.mjs": "astro",
            "astro.config.ts": "astro",
            "next.config.js": "nextjs",
            "next.config.ts": "nextjs",
            "_config.yml": "jekyll",
            "config.toml": "hugo",
        }
        resp = await client.get(
            f"{GH_API}/repos/{self.owner}/{self.repo}/contents/",
            headers=self._headers(),
        )
        if resp.status_code == 200:
            files = {f["name"] for f in resp.json() if isinstance(resp.json(), list)}
            for marker, fw in markers.items():
                if marker in files:
                    return fw
        return "unknown"

    async def list_pages(self, limit: int = 500) -> list[CMSPage]:
        """List markdown/MDX files that likely contain SEO metadata."""
        pages: list[CMSPage] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/trees/{self.branch}",
                params={"recursive": "1"},
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return pages

            tree = resp.json().get("tree", [])
            md_files = [
                f for f in tree
                if f["type"] == "blob" and f["path"].endswith((".md", ".mdx"))
            ][:limit]

            for f in md_files:
                pages.append(CMSPage(
                    id=f["sha"],
                    url=f"/{f['path']}",
                    title=f["path"].split("/")[-1].replace(".md", "").replace(".mdx", ""),
                    meta_description="",
                    raw={"path": f["path"], "sha": f["sha"]},
                ))
        return pages

    async def get_page(self, page_id: str) -> CMSPage:
        raise NotImplementedError("Use list_pages() and the raw path to fetch content.")

    async def apply_fix(self, page_id: str, field: str, new_value: str) -> ApplyResult:
        """Create a branch and PR with the SEO fix applied to the file.

        page_id must be the file path (e.g. src/pages/about.mdx).
        """
        if not self.token:
            return ApplyResult(
                success=False,
                message="GitHub token not configured. Connect your GitHub account in Integrations.",
            )

        async with httpx.AsyncClient(timeout=20.0) as client:
            # 1. Get current file content and SHA
            resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{page_id}",
                params={"ref": self.branch},
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return ApplyResult(success=False, message=f"File {page_id} not found in repo")

            file_data = resp.json()
            current_content = base64.b64decode(file_data["content"]).decode("utf-8")
            file_sha = file_data["sha"]

            # 2. Apply the SEO fix to the content (frontmatter update)
            updated_content, old_value = _patch_frontmatter(current_content, field, new_value)

            # 3. Create a new branch for the fix
            fix_branch = f"autoseo/fix-{field}-{page_id.replace('/', '-')[:40]}"
            base_resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/ref/heads/{self.branch}",
                headers=self._headers(),
            )
            if base_resp.status_code != 200:
                return ApplyResult(success=False, message="Could not get base branch SHA")

            base_sha = base_resp.json()["object"]["sha"]
            await client.post(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/refs",
                json={"ref": f"refs/heads/{fix_branch}", "sha": base_sha},
                headers=self._headers(),
            )

            # 4. Commit the updated file
            commit_resp = await client.put(
                f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{page_id}",
                json={
                    "message": f"fix(seo): update {field} for {page_id}",
                    "content": base64.b64encode(updated_content.encode()).decode(),
                    "sha": file_sha,
                    "branch": fix_branch,
                },
                headers=self._headers(),
            )
            if commit_resp.status_code not in (200, 201):
                return ApplyResult(success=False, message=f"Commit failed: {commit_resp.text[:200]}")

            # 5. Open a Pull Request
            pr_resp = await client.post(
                f"{GH_API}/repos/{self.owner}/{self.repo}/pulls",
                json={
                    "title": f"AutoSEO: Update {field} on {page_id}",
                    "head": fix_branch,
                    "base": self.branch,
                    "body": f"## SEO Fix\n\n**Field:** `{field}`\n**File:** `{page_id}`\n\n**Before:** `{old_value}`\n**After:** `{new_value}`\n\n> Generated by AutoSEO. Review and merge to apply.",
                },
                headers=self._headers(),
            )

            if pr_resp.status_code == 201:
                pr_url = pr_resp.json().get("html_url", "")
                return ApplyResult(
                    success=True,
                    message=f"PR created: {pr_url}",
                    rollback_value=old_value,
                )
            return ApplyResult(success=False, message=f"PR creation failed: {pr_resp.text[:200]}")


def _patch_frontmatter(content: str, field: str, new_value: str) -> tuple[str, str]:
    """Update a frontmatter field in a markdown file. Returns (updated_content, old_value)."""
    import re
    fm_pattern = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
    match = fm_pattern.match(content)
    if not match:
        # No frontmatter — prepend it
        new_fm = f"---\n{field}: \"{new_value}\"\n---\n"
        return new_fm + content, ""

    fm_body = match.group(1)
    field_pattern = re.compile(rf"^({re.escape(field)}:\s*)(.+)$", re.MULTILINE)
    fm_match = field_pattern.search(fm_body)
    old_value = fm_match.group(2).strip('" \'') if fm_match else ""

    if fm_match:
        new_fm_body = field_pattern.sub(rf'\g<1>"{new_value}"', fm_body)
    else:
        new_fm_body = fm_body + f'\n{field}: "{new_value}"'

    new_content = content[:match.start(1)] + new_fm_body + content[match.end(1):]
    return new_content, old_value
