"""Upgrade github_scanner to use real GitHub API"""
import os, ast

BASE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(BASE, "modules", "github_scanner.py")

with open(src, encoding="utf-8") as f:
    code = f.read()

# Add real HTTP import after existing imports
lines = code.split("\n")
insert_at = None
for i, l in enumerate(lines):
    if l.startswith("import ") or l.startswith("from "):
        insert_at = i + 1
    if l.strip().startswith("__module_meta__") and insert_at is None:
        insert_at = i
        break

real_imports = [
    "",
    "import requests",
    "from datetime import datetime, timezone",
    "import time",
    "import json",
]

# Insert after last import line
if insert_at:
    for li in reversed(real_imports):
        lines.insert(insert_at, li)

new_code = "\n".join(lines)

# Add real scan method before the module_class line
old_execute = """    async def execute(self, action: str, params: dict = None) -> Any:
        return await self._safe_execute(action, params, handler=self._dispatch)"""

new_execute = """    async def execute(self, action: str, params: dict = None) -> Any:
        return await self._safe_execute(action, params, handler=self._dispatch)

    # ── Real GitHub API ──

    async def scan_repos(self, query: str = "AI", language: str = "", per_page: int = 10) -> dict:
        \"\"\"真实 GitHub REST API 搜索仓库\"\"\"
        q_parts = [query]
        if language:
            q_parts.append(f"language:{language}")
        q = "+".join(q_parts)
        url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page={per_page}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AUTO-EVO-AI-V0.1",
        }
        token = self.config.get("github_token", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        t0 = time.time()
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            elapsed = time.time() - t0
            if resp.status_code == 403:
                return {"success": False, "error": "rate_limited", "retry_after": 60, "status_code": 403}
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            repos = []
            for item in items[:per_page]:
                repos.append({
                    "name": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "description": (item.get("description") or "")[:200],
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0),
                    "language": item.get("language") or "",
                    "topics": item.get("topics", []),
                    "updated_at": item.get("updated_at", ""),
                })
            logger.info(f"github scan: {q} -> {len(repos)} repos in {elapsed:.1f}s")
            return {"success": True, "repos": repos, "total": data.get("total_count", 0), "elapsed_s": round(elapsed, 2)}
        except requests.Timeout:
            return {"success": False, "error": "timeout", "elapsed_s": round(time.time() - t0, 2)}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)[:100], "status_code": getattr(e.response, 'status_code', 0)}"""

if old_execute in new_code:
    new_code = new_code.replace(old_execute, new_execute)

with open(src, "w", encoding="utf-8") as f:
    f.write(new_code)

print(f"Updated: {src}")
print(f"requests import: {'import requests' in new_code}")
print(f"scan_repos method: {'async def scan_repos' in new_code}")
