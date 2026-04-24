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
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

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
        project_root: str = "",
    ):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.branch = branch
        self.project_root = project_root.strip().strip("/")
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
            "vite.config.js": "vite_react",
            "vite.config.ts": "vite_react",
            "vite.config.mjs": "vite_react",
            "vite.config.mts": "vite_react",
            "remix.config.js": "remix",
            "remix.config.ts": "remix",
            "_config.yml": "jekyll",
            "config.toml": "hugo",
        }
        resp = await client.get(
            f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{self.project_root}",
            headers=self._headers(),
        )
        if resp.status_code == 200:
            files = {f["name"] for f in resp.json() if isinstance(resp.json(), list)}
            for marker, fw in markers.items():
                if marker in files:
                    return fw
            if "package.json" in files and "src" in files and "public" in files:
                return "react_spa"
        return "unknown"

    async def analyze_static_app(self, project_root: str | None = None) -> dict:
        """Return a small repository readiness report for static-app SEO fixes."""
        root = (project_root if project_root is not None else self.project_root).strip().strip("/")
        prefix = f"{root}/" if root else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            tree_resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/trees/{self.branch}",
                params={"recursive": "1"},
                headers=self._headers(),
            )
            if tree_resp.status_code != 200:
                return {
                    "framework": "unknown",
                    "project_root": root,
                    "error": f"Could not list repository tree: {tree_resp.status_code}",
                    "safe_file_fixes": [],
                    "plan_only_fixes": [],
                }

            paths = {
                item.get("path", "")
                for item in tree_resp.json().get("tree", [])
                if item.get("type") == "blob"
            }
            root_paths = {path[len(prefix):] for path in paths if not prefix or path.startswith(prefix)}

            framework = "unknown"
            if any(path.startswith(("vite.config.",)) for path in root_paths):
                framework = "vite_react"
            elif any(path.startswith(("next.config.",)) for path in root_paths) or any(path.startswith(("app/", "pages/")) for path in root_paths):
                framework = "nextjs"
            elif any(path.startswith(("astro.config.",)) for path in root_paths):
                framework = "astro"
            elif any(path.startswith(("remix.config.",)) for path in root_paths):
                framework = "remix"
            elif "package.json" in root_paths and any(path.startswith("src/") for path in root_paths):
                framework = "react_spa"
            elif "index.html" in root_paths:
                framework = "static_html"

            package_manager = "npm"
            if "pnpm-lock.yaml" in root_paths:
                package_manager = "pnpm"
            elif "yarn.lock" in root_paths:
                package_manager = "yarn"
            elif "bun.lockb" in root_paths or "bun.lock" in root_paths:
                package_manager = "bun"

            return {
                "framework": framework,
                "project_root": root,
                "package_manager": package_manager,
                "files_found": sorted(path for path in root_paths if path in {"package.json", "index.html", "src/App.tsx", "src/main.tsx", "public/robots.txt", "public/sitemap.xml"} or path.startswith(("vite.config.", "next.config.", "astro.config.", "remix.config."))),
                "safe_file_fixes": ["missing_robots", "missing_sitemap"],
                "plan_only_fixes": [
                    "spa_no_prerender",
                    "duplicate_title",
                    "stale_schema_date",
                    "unverified_review_schema",
                    "missing_offer_schema",
                    "broken_og_image",
                ],
            }

    async def repository_tree(self, project_root: str | None = None) -> list[dict]:
        """Return repository blob paths under the configured project root."""
        root = (project_root if project_root is not None else self.project_root).strip().strip("/")
        prefix = f"{root}/" if root else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/trees/{self.branch}",
                params={"recursive": "1"},
                headers=self._headers(),
            )
        if response.status_code != 200:
            raise ValueError(f"Could not list repository tree: {response.status_code}")
        out: list[dict] = []
        for item in response.json().get("tree", []):
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if prefix and not path.startswith(prefix):
                continue
            out.append({
                "path": path,
                "size": item.get("size") or 0,
                "sha": item.get("sha"),
            })
        return out

    async def candidate_files_for_issue(
        self,
        issue_type: str,
        *,
        project_root: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Pick small, likely-relevant files for AI patch planning."""
        tree = await self.repository_tree(project_root)
        preferred_names = {
            "index.html",
            "package.json",
            "src/App.tsx",
            "src/App.jsx",
            "src/main.tsx",
            "src/main.jsx",
            "src/routes.tsx",
            "src/routes.jsx",
            "app/layout.tsx",
            "app/page.tsx",
            "pages/_app.tsx",
            "pages/_document.tsx",
        }
        keywords = {
            "spa_no_prerender": ("vite", "next", "astro", "remix", "router", "routes", "helmet", "metadata", "seo"),
            "duplicate_title": ("title", "metadata", "seo", "helmet", "routes", "router", "app", "layout"),
            "stale_schema_date": ("schema", "jsonld", "json-ld", "structured", "pricing", "offer"),
            "unverified_review_schema": ("review", "rating", "testimonial", "schema", "jsonld", "json-ld"),
            "missing_offer_schema": ("pricing", "offer", "schema", "jsonld", "json-ld", "product"),
            "broken_og_image": ("og", "open-graph", "opengraph", "metadata", "seo", "image"),
        }.get(issue_type, ("seo", "metadata", "routes", "app"))
        allowed_suffixes = (
            ".astro", ".html", ".js", ".jsx", ".json", ".md", ".mdx", ".mjs",
            ".ts", ".tsx",
        )

        scored: list[tuple[int, dict]] = []
        root = (project_root if project_root is not None else self.project_root).strip().strip("/")
        prefix = f"{root}/" if root else ""
        for item in tree:
            path = item["path"]
            lower = path.lower()
            if item.get("size", 0) > 70000 or not lower.endswith(allowed_suffixes):
                continue
            score = 0
            rel = path[len(prefix):] if prefix and path.startswith(prefix) else path
            if rel in preferred_names:
                score += 40
            if lower.endswith(("vite.config.ts", "vite.config.js", "next.config.js", "next.config.ts", "astro.config.mjs", "astro.config.ts")):
                score += 20
            score += sum(12 for keyword in keywords if keyword in lower)
            if "/src/" in f"/{lower}" or lower.startswith("src/"):
                score += 5
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1]["path"]))
        return [item for _score, item in scored[:limit]]

    async def read_text_files(self, paths: list[str], *, ref: str | None = None, max_chars: int = 70000) -> list[dict]:
        """Read text file contents from GitHub for AI context."""
        out: list[dict] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for path in paths:
                response = await client.get(
                    f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{path}",
                    params={"ref": ref or self.branch},
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    continue
                data = response.json()
                if data.get("encoding") != "base64" or data.get("type") != "file":
                    continue
                content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
                out.append({
                    "path": path,
                    "sha": data.get("sha"),
                    "content": content[:max_chars],
                })
        return out

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
        """Fetch a single markdown/MDX file by path and parse its frontmatter.

        page_id may be a file SHA OR the file path directly.
        """
        path = page_id if "/" in page_id or page_id.endswith((".md", ".mdx")) else None
        async with httpx.AsyncClient(timeout=10.0) as client:
            if path is None:
                # Fall back to tree lookup by SHA
                tree_resp = await client.get(
                    f"{GH_API}/repos/{self.owner}/{self.repo}/git/trees/{self.branch}",
                    params={"recursive": "1"},
                    headers=self._headers(),
                )
                if tree_resp.status_code != 200:
                    raise ValueError(f"Could not list tree for {self.owner}/{self.repo}")
                for f in tree_resp.json().get("tree", []):
                    if f.get("sha") == page_id:
                        path = f.get("path")
                        break
                if path is None:
                    raise ValueError(f"Could not resolve page_id {page_id} to a file path")

            resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{path}",
                params={"ref": self.branch},
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise ValueError(f"File {path} not found in {self.owner}/{self.repo}")
            data = resp.json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            fm = _read_frontmatter(content)
            return CMSPage(
                id=path,
                url=f"/{path}",
                title=fm.get("title", path.rsplit("/", 1)[-1]),
                meta_description=fm.get("description") or fm.get("metaDescription") or "",
                canonical_url=fm.get("canonical"),
                raw={"path": path, "sha": data["sha"], "frontmatter": fm},
            )

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

    async def create_static_fix_pr(
        self,
        *,
        issue_type: str,
        title: str,
        site_domain: str,
        affected_urls: list[str],
        manual_steps: list[str],
        project_root: str = "",
        build_command: str | None = None,
        package_manager: str | None = None,
    ) -> dict:
        """Create a reviewable PR for a grouped static-app SEO fix.

        For safe site-root assets we patch files directly. For structural SPA
        problems we create a clear PR plan rather than pretending AutoSEO knows
        enough to rewrite the app safely.
        """
        root = (project_root or self.project_root).strip().strip("/")
        normalized_domain = site_domain if site_domain.startswith(("http://", "https://")) else f"https://{site_domain}"
        base_url = normalized_domain.rstrip("/")
        safe_issue_file_fixes = issue_type in {"missing_robots", "missing_sitemap"}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        branch = f"autoseo/{issue_type.replace('_', '-')}-{timestamp}"

        analysis = await self.analyze_static_app(root)
        files = self._static_fix_files(
            issue_type=issue_type,
            root=root,
            base_url=base_url,
            affected_urls=affected_urls,
            manual_steps=manual_steps,
            analysis=analysis,
        )
        mode = "file_patch" if safe_issue_file_fixes and files else "plan_only"
        if mode == "plan_only":
            files = {
                self._rooted_path(root, f"autoseo-fix-plans/{issue_type}-{timestamp}.md"): self._plan_markdown(
                    issue_type=issue_type,
                    title=title,
                    site_domain=base_url,
                    affected_urls=affected_urls,
                    manual_steps=manual_steps,
                    analysis=analysis,
                    build_command=build_command,
                    package_manager=package_manager,
                )
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            base_resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/ref/heads/{self.branch}",
                headers=self._headers(),
            )
            if base_resp.status_code != 200:
                return {"success": False, "message": "Could not get base branch SHA", "status_code": base_resp.status_code}

            base_sha = base_resp.json()["object"]["sha"]
            branch_resp = await client.post(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": base_sha},
                headers=self._headers(),
            )
            if branch_resp.status_code not in (201, 422):
                return {"success": False, "message": f"Could not create branch: {branch_resp.text[:200]}", "status_code": branch_resp.status_code}

            committed_paths: list[str] = []
            for path, content in files.items():
                existing_sha = await self._file_sha(client, path, branch)
                payload = {
                    "message": f"fix(seo): {title}",
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "branch": branch,
                }
                if existing_sha:
                    payload["sha"] = existing_sha
                commit_resp = await client.put(
                    f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{path}",
                    json=payload,
                    headers=self._headers(),
                )
                if commit_resp.status_code not in (200, 201):
                    return {"success": False, "message": f"Commit failed for {path}: {commit_resp.text[:200]}", "status_code": commit_resp.status_code}
                committed_paths.append(path)

            pr_body = self._pr_body(
                issue_type=issue_type,
                title=title,
                site_domain=base_url,
                affected_urls=affected_urls,
                manual_steps=manual_steps,
                analysis=analysis,
                mode=mode,
                files=committed_paths,
            )
            pr_resp = await client.post(
                f"{GH_API}/repos/{self.owner}/{self.repo}/pulls",
                json={
                    "title": f"AutoSEO: {title}",
                    "head": branch,
                    "base": self.branch,
                    "body": pr_body,
                },
                headers=self._headers(),
            )
            if pr_resp.status_code != 201:
                return {"success": False, "message": f"PR creation failed: {pr_resp.text[:200]}", "status_code": pr_resp.status_code}

            data = pr_resp.json()
            return {
                "success": True,
                "mode": mode,
                "message": "GitHub PR created",
                "pr_url": data.get("html_url"),
                "pr_number": data.get("number"),
                "branch": branch,
                "files_changed": committed_paths,
                "repo_analysis": analysis,
            }

    async def create_ai_patch_pr(
        self,
        *,
        issue_type: str,
        title: str,
        site_domain: str,
        affected_urls: list[str],
        preview: dict,
        project_root: str = "",
    ) -> dict:
        """Create a PR from a validated AI preview."""
        from packages.shared.patch_safety import validate_file_changes

        root = (project_root or self.project_root).strip().strip("/")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        branch = f"autoseo/ai-{issue_type.replace('_', '-')}-{timestamp}"
        changes = preview.get("file_changes") or []
        safety = validate_file_changes(changes, project_root=root)
        mode = "file_patch" if safety.ok and safety.sanitized_changes else "plan_only"
        if mode == "plan_only":
            safety_note = "\n".join(f"- {item}" for item in (safety.errors or preview.get("review_notes") or []))
            changes = [
                {
                    "path": self._rooted_path(root, f"autoseo-fix-plans/{issue_type}-{timestamp}.md"),
                    "action": "create",
                    "summary": "AI fix plan",
                    "content": self._ai_plan_markdown(
                        issue_type=issue_type,
                        title=title,
                        site_domain=site_domain,
                        affected_urls=affected_urls,
                        preview=preview,
                        safety_note=safety_note,
                    ),
                }
            ]
            safety = validate_file_changes(changes, project_root="")
            if not safety.ok:
                return {"success": False, "message": "AI plan failed safety validation", "safety": safety.__dict__}

        draft = preview.get("risk_level") == "high" or mode == "plan_only"

        async with httpx.AsyncClient(timeout=30.0) as client:
            base_resp = await client.get(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/ref/heads/{self.branch}",
                headers=self._headers(),
            )
            if base_resp.status_code != 200:
                return {"success": False, "message": "Could not get base branch SHA", "status_code": base_resp.status_code}
            base_sha = base_resp.json()["object"]["sha"]
            branch_resp = await client.post(
                f"{GH_API}/repos/{self.owner}/{self.repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": base_sha},
                headers=self._headers(),
            )
            if branch_resp.status_code not in (201, 422):
                return {"success": False, "message": f"Could not create branch: {branch_resp.text[:200]}", "status_code": branch_resp.status_code}

            committed_paths: list[str] = []
            for change in safety.sanitized_changes:
                path = change["path"]
                existing_sha = await self._file_sha(client, path, branch)
                payload = {
                    "message": f"fix(seo): {change['summary']}",
                    "content": base64.b64encode(change["content"].encode("utf-8")).decode("ascii"),
                    "branch": branch,
                }
                if existing_sha:
                    payload["sha"] = existing_sha
                commit_resp = await client.put(
                    f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{path}",
                    json=payload,
                    headers=self._headers(),
                )
                if commit_resp.status_code not in (200, 201):
                    return {"success": False, "message": f"Commit failed for {path}: {commit_resp.text[:200]}", "status_code": commit_resp.status_code}
                committed_paths.append(path)

            pr_resp = await client.post(
                f"{GH_API}/repos/{self.owner}/{self.repo}/pulls",
                json={
                    "title": f"AutoSEO AI: {title}",
                    "head": branch,
                    "base": self.branch,
                    "draft": draft,
                    "body": self._ai_pr_body(
                        issue_type=issue_type,
                        title=title,
                        site_domain=site_domain,
                        affected_urls=affected_urls,
                        preview=preview,
                        mode=mode,
                        files=committed_paths,
                    ),
                },
                headers=self._headers(),
            )
            if pr_resp.status_code != 201:
                return {"success": False, "message": f"PR creation failed: {pr_resp.text[:200]}", "status_code": pr_resp.status_code}

            data = pr_resp.json()
            return {
                "success": True,
                "mode": mode,
                "message": "GitHub PR created from AI preview",
                "pr_url": data.get("html_url"),
                "pr_number": data.get("number"),
                "branch": branch,
                "draft": draft,
                "files_changed": committed_paths,
                "risk_level": preview.get("risk_level"),
                "ai_model": preview.get("ai_model"),
                "safety": safety.__dict__,
            }

    async def _file_sha(self, client: httpx.AsyncClient, path: str, branch: str) -> str | None:
        resp = await client.get(
            f"{GH_API}/repos/{self.owner}/{self.repo}/contents/{path}",
            params={"ref": branch},
            headers=self._headers(),
        )
        if resp.status_code == 200:
            return resp.json().get("sha")
        return None

    def _rooted_path(self, root: str, path: str) -> str:
        return f"{root.strip().strip('/')}/{path}" if root else path

    def _static_fix_files(
        self,
        *,
        issue_type: str,
        root: str,
        base_url: str,
        affected_urls: list[str],
        manual_steps: list[str],
        analysis: dict,
    ) -> dict[str, str]:
        urls = _clean_urls([base_url, *affected_urls])
        if issue_type == "missing_robots":
            return {
                self._rooted_path(root, "public/robots.txt"): (
                    "User-agent: *\n"
                    "Allow: /\n"
                    f"Sitemap: {base_url}/sitemap.xml\n"
                )
            }
        if issue_type == "missing_sitemap":
            url_entries = "\n".join(
                f"  <url><loc>{url}</loc></url>"
                for url in urls[:500]
            )
            return {
                self._rooted_path(root, "public/sitemap.xml"): (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                    f"{url_entries}\n"
                    "</urlset>\n"
                )
            }
        return {}

    def _plan_markdown(
        self,
        *,
        issue_type: str,
        title: str,
        site_domain: str,
        affected_urls: list[str],
        manual_steps: list[str],
        analysis: dict,
        build_command: str | None,
        package_manager: str | None,
    ) -> str:
        affected = "\n".join(f"- {url}" for url in _clean_urls(affected_urls)[:25]) or "- Site-wide issue"
        steps = "\n".join(f"{index}. {step}" for index, step in enumerate(manual_steps, start=1))
        return (
            f"# AutoSEO Fix Plan: {title}\n\n"
            f"- Issue type: `{issue_type}`\n"
            f"- Site: {site_domain}\n"
            f"- Detected framework: `{analysis.get('framework', 'unknown')}`\n"
            f"- Project root: `{analysis.get('project_root') or '.'}`\n"
            f"- Package manager: `{package_manager or analysis.get('package_manager', 'unknown')}`\n"
            f"- Build command: `{build_command or 'not configured'}`\n\n"
            "## Affected URLs\n"
            f"{affected}\n\n"
            "## Required implementation\n"
            f"{steps}\n\n"
            "## Review notes\n"
            "AutoSEO created a plan-only PR because this fix changes app structure or business data. "
            "Review the route, schema, and rendering code before merging.\n"
        )

    def _pr_body(
        self,
        *,
        issue_type: str,
        title: str,
        site_domain: str,
        affected_urls: list[str],
        manual_steps: list[str],
        analysis: dict,
        mode: str,
        files: list[str],
    ) -> str:
        affected = "\n".join(f"- {url}" for url in _clean_urls(affected_urls)[:25]) or "- Site-wide issue"
        changed = "\n".join(f"- `{path}`" for path in files) or "- No source files changed"
        steps = "\n".join(f"- {step}" for step in manual_steps)
        return (
            f"## AutoSEO root-cause fix\n\n"
            f"**Issue:** `{issue_type}` - {title}\n"
            f"**Site:** {site_domain}\n"
            f"**Mode:** `{mode}`\n"
            f"**Detected framework:** `{analysis.get('framework', 'unknown')}`\n\n"
            "### Files changed\n"
            f"{changed}\n\n"
            "### Affected URLs\n"
            f"{affected}\n\n"
            "### What to review\n"
            f"{steps}\n\n"
            "After merging and deploying, run a new AutoSEO crawl to verify the grouped issue count drops.\n"
        )

    def _ai_plan_markdown(
        self,
        *,
        issue_type: str,
        title: str,
        site_domain: str,
        affected_urls: list[str],
        preview: dict,
        safety_note: str,
    ) -> str:
        affected = "\n".join(f"- {url}" for url in _clean_urls(affected_urls)[:25]) or "- Site-wide issue"
        notes = "\n".join(f"- {note}" for note in preview.get("review_notes", [])) or "- Review the plan before making source changes."
        missing = "\n".join(f"- {item}" for item in preview.get("missing_user_data", [])) or "- None"
        return (
            f"# AutoSEO AI Fix Plan: {title}\n\n"
            f"- Issue type: `{issue_type}`\n"
            f"- Site: {site_domain}\n"
            f"- Risk level: `{preview.get('risk_level', 'high')}`\n"
            f"- Mode: `plan_only`\n\n"
            "## Summary\n"
            f"{preview.get('patch_summary') or preview.get('summary') or 'Review and implement this root-cause fix.'}\n\n"
            "## Affected URLs\n"
            f"{affected}\n\n"
            "## Missing user data\n"
            f"{missing}\n\n"
            "## Review notes\n"
            f"{notes}\n\n"
            "## Safety notes\n"
            f"{safety_note or '- No blocking safety issues.'}\n"
        )

    def _ai_pr_body(
        self,
        *,
        issue_type: str,
        title: str,
        site_domain: str,
        affected_urls: list[str],
        preview: dict,
        mode: str,
        files: list[str],
    ) -> str:
        affected = "\n".join(f"- {url}" for url in _clean_urls(affected_urls)[:25]) or "- Site-wide issue"
        changed = "\n".join(f"- `{path}`" for path in files) or "- No source files changed"
        notes = "\n".join(f"- {note}" for note in preview.get("review_notes", [])) or "- Review the diff, deploy, then re-crawl."
        missing = "\n".join(f"- {item}" for item in preview.get("missing_user_data", [])) or "- None"
        return (
            "## AutoSEO AI root-cause fix\n\n"
            f"**Issue:** `{issue_type}` - {title}\n"
            f"**Site:** {site_domain}\n"
            f"**Mode:** `{mode}`\n"
            f"**Risk:** `{preview.get('risk_level', 'unknown')}`\n"
            f"**AI model:** `{preview.get('ai_model') or 'not used'}`\n\n"
            "### Patch summary\n"
            f"{preview.get('patch_summary') or preview.get('summary') or 'No summary returned.'}\n\n"
            "### Files changed\n"
            f"{changed}\n\n"
            "### Affected URLs\n"
            f"{affected}\n\n"
            "### Missing user data\n"
            f"{missing}\n\n"
            "### Review notes\n"
            f"{notes}\n\n"
            "Merge only after reviewing the diff. After deployment, run a new AutoSEO crawl; AutoSEO should mark this fixed only after the issue disappears.\n"
        )


def _read_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from a markdown/MDX file (lightweight, no PyYAML).

    Only handles the simple key: value lines we generate. Falls back to {} on
    any parse difficulty so we never raise from a benign file.
    """
    import re
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    out: dict = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


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


def _clean_urls(urls: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if not url:
            continue
        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
        if not parsed.netloc:
            continue
        cleaned = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
        if parsed.query:
            cleaned = f"{cleaned}?{parsed.query}"
        if cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out
