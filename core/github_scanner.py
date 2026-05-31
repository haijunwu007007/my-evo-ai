"""
AUTO-EVO-AI V0.1 — GitHub 智能扫描引擎
========================================
上市公司级自动扫描系统：
  1. 依赖更新扫描 — 监控32+已集成依赖的最新版本
  2. GitHub Trending扫描 — 每日发现优质开源项目
  3. 智能推荐评估 — 基于Stars/Forks/活跃度/相关性评分
  4. 自动集成建议 — 生成集成方案和代码模板
  5. 变更日志追踪 — 追踪关键依赖的Breaking Changes
"""

import os
import re
import json
import time
import asyncio
import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("GitHubScanner")

# ─── 已集成的依赖清单 ───
INTEGRATED_DEPS = {
    # Web框架
    "fastapi": {"category": "web", "pypi": "fastapi", "installed": "0.115.0", "critical": True},
    "uvicorn": {"category": "web", "pypi": "uvicorn", "installed": "0.32.0", "critical": True},
    "starlette": {"category": "web", "pypi": "starlette", "installed": None, "critical": False},
    "pydantic": {"category": "web", "pypi": "pydantic", "installed": "2.10.0", "critical": True},
    # 数据处理
    "pandas": {"category": "data", "pypi": "pandas", "installed": None, "critical": False},
    "numpy": {"category": "data", "pypi": "numpy", "installed": None, "critical": False},
    "openpyxl": {"category": "data", "pypi": "openpyxl", "installed": None, "critical": False},
    # 数据库
    "redis": {"category": "database", "pypi": "redis", "installed": None, "critical": False},
    "psycopg2": {"category": "database", "pypi": "psycopg2-binary", "installed": None, "critical": False},
    # AI/ML
    "chromadb": {"category": "ai", "pypi": "chromadb", "installed": "0.5.0", "critical": False},
    # 文档生成
    "python-docx": {"category": "doc", "pypi": "python-docx", "installed": None, "critical": False},
    "python-pptx": {"category": "doc", "pypi": "python-pptx", "installed": None, "critical": False},
    "markdown": {"category": "doc", "pypi": "markdown", "installed": None, "critical": False},
    # HTTP客户端
    "aiohttp": {"category": "http", "pypi": "aiohttp", "installed": None, "critical": False},
    "httpx": {"category": "http", "pypi": "httpx", "installed": None, "critical": False},
    "requests": {"category": "http", "pypi": "requests", "installed": "2.32.0", "critical": True},
    # 安全
    "cryptography": {"category": "security", "pypi": "cryptography", "installed": None, "critical": False},
    # 工具
    "psutil": {"category": "util", "pypi": "psutil", "installed": "5.9.8", "critical": True},
    "pyyaml": {"category": "util", "pypi": "pyyaml", "installed": None, "critical": True},
    "tenacity": {"category": "util", "pypi": "tenacity", "installed": None, "critical": False},
    "apscheduler": {"category": "util", "pypi": "apscheduler", "installed": None, "critical": False},
    # 浏览器
    "playwright": {"category": "browser", "pypi": "playwright", "installed": None, "critical": False},
    "selenium": {"category": "browser", "pypi": "selenium", "installed": None, "critical": False},
    # 金融
    "akshare": {"category": "finance", "pypi": "akshare", "installed": None, "critical": False},
    # 熔断
    "pybreaker": {"category": "reliability", "pypi": "pybreaker", "installed": None, "critical": False},
    # 网络
    "pyngrok": {"category": "network", "pypi": "pyngrok", "installed": None, "critical": False},
    # 桌面
    "pywinauto": {"category": "desktop", "pypi": "pywinauto", "installed": None, "critical": False},
    # 压缩
    "zstandard": {"category": "util", "pypi": "zstandard", "installed": None, "critical": False},
    # 数据库
    "mysql": {"category": "database", "pypi": "mysql-connector-python", "installed": None, "critical": False},
}

# ─── 关注的开源项目（GitHub） ───
TRACKED_REPOS = {
    "tiangolo/fastapi": {"category": "web", "reason": "核心Web框架"},
    "encode/uvicorn": {"category": "web", "reason": "ASGI服务器"},
    "pydantic/pydantic": {"category": "web", "reason": "数据验证"},
    "pallets/flask": {"category": "web", "reason": "轻量Web框架参考"},
    "pandas-dev/pandas": {"category": "data", "reason": "数据分析"},
    "numpy/numpy": {"category": "data", "reason": "数值计算"},
    "redis/redis-py": {"category": "database", "reason": "Redis客户端"},
    "psycopg/psycopg": {"category": "database", "reason": "PostgreSQL客户端"},
    "chroma-core/chroma": {"category": "ai", "reason": "向量数据库"},
    "playwright/python": {"category": "browser", "reason": "浏览器自动化"},
    "SeleniumHQ/selenium": {"category": "browser", "reason": "浏览器自动化"},
    "aio-libs/aiohttp": {"category": "http", "reason": "异步HTTP"},
    "encode/httpx": {"category": "http", "reason": "现代HTTP客户端"},
    "psf/requests": {"category": "http", "reason": "HTTP客户端"},
    "pyca/cryptography": {"category": "security", "reason": "加密库"},
    "giampaolo/psutil": {"category": "util", "reason": "系统监控"},
    "jgeboski/pybreaker": {"category": "reliability", "reason": "熔断器"},
    "agronholm/apscheduler": {"category": "util", "reason": "定时调度"},
}

# ─── Trending扫描关键词 ───
TRENDING_KEYWORDS = [
    "python", "agent", "llm", "ai", "automation", "workflow",
    "fastapi", "api", "dashboard", "monitoring", "observability",
    "security", "devops", "cicd", "pipeline", "orchestration",
    "vector-database", "rag", "embedding", "chatbot", "copilot",
]


class ScanType(str, Enum):
    DEPENDENCY = "dependency"       # 依赖更新检查
    TRENDING = "trending"           # GitHub Trending
    TRACKED = "tracked"             # 关注仓库更新
    FULL = "full"                   # 全量扫描


class RecommendationLevel(str, Enum):
    CRITICAL = "critical"   # 重大更新（安全/兼容性）
    HIGH = "high"           # 重要更新
    MEDIUM = "medium"       # 建议更新
    LOW = "low"             # 可选更新
    INFO = "info"           # 信息


@dataclass
class DependencyUpdate:
    """依赖更新信息"""
    package: str
    installed_version: str
    latest_version: str
    category: str
    critical: bool
    changelog_url: str = ""
    publish_date: str = ""
    level: str = "medium"
    notes: str = ""


@dataclass
class TrendingProject:
    """Trending项目"""
    name: str
    full_name: str
    url: str
    description: str
    language: str
    stars: int
    forks: int
    today_stars: int = 0
    category: str = ""
    recommendation: str = "medium"
    integration_idea: str = ""
    scanned_at: str = ""


@dataclass
class TrackedRepoUpdate:
    """关注仓库更新"""
    repo: str
    category: str
    latest_release: str
    release_url: str
    release_date: str = ""
    changelog: str = ""
    has_breaking: bool = False
    needs_attention: bool = False


@dataclass
class ScanReport:
    """扫描报告"""
    scan_id: str
    scan_type: str
    started_at: str
    finished_at: str = ""
    duration_ms: int = 0
    status: str = "running"
    dependency_updates: list = field(default_factory=list)
    trending_projects: list = field(default_factory=list)
    tracked_updates: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


class GitHubScannerStore:
    """SQLite持久化存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            base = os.environ.get("EVO_DATA_DIR", ".evo_data")
            os.makedirs(base, exist_ok=True)
            db_path = os.path.join(base, "github_scanner.db")
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS scan_reports (
                    id TEXT PRIMARY KEY,
                    scan_type TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_ms INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    summary TEXT DEFAULT '{}',
                    error TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS dependency_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    package TEXT,
                    installed_version TEXT,
                    latest_version TEXT,
                    category TEXT,
                    critical INTEGER DEFAULT 0,
                    level TEXT DEFAULT 'medium',
                    changelog_url TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    publish_date TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS trending_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    name TEXT,
                    full_name TEXT,
                    url TEXT,
                    description TEXT DEFAULT '',
                    language TEXT DEFAULT '',
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    today_stars INTEGER DEFAULT 0,
                    recommendation TEXT DEFAULT 'medium',
                    integration_idea TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    scanned_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS tracked_repos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    repo TEXT,
                    category TEXT,
                    latest_release TEXT DEFAULT '',
                    release_url TEXT DEFAULT '',
                    release_date TEXT DEFAULT '',
                    changelog TEXT DEFAULT '',
                    has_breaking INTEGER DEFAULT 0,
                    needs_attention INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS scan_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_dep_package ON dependency_updates(package);
                CREATE INDEX IF NOT EXISTS idx_trending_stars ON trending_projects(stars DESC);
                CREATE INDEX IF NOT EXISTS idx_report_type ON scan_reports(scan_type);
                CREATE INDEX IF NOT EXISTS idx_report_date ON scan_reports(created_at);
            """)

    def save_report(self, report: ScanReport):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO scan_reports (id,scan_type,started_at,finished_at,duration_ms,status,summary,error) VALUES (?,?,?,?,?,?,?,?)",
                (report.scan_id, report.scan_type, report.started_at, report.finished_at,
                 report.duration_ms, report.status, json.dumps(report.summary, ensure_ascii=False),
                 "; ".join(report.errors) if report.errors else "")
            )
            for dep in report.dependency_updates:
                c.execute(
                    "INSERT INTO dependency_updates (report_id,package,installed_version,latest_version,category,critical,level,changelog_url,notes,publish_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (report.scan_id, dep.package, dep.installed_version, dep.latest_version,
                     dep.category, 1 if dep.critical else 0, dep.level, dep.changelog_url,
                     dep.notes, dep.publish_date)
                )
            for proj in report.trending_projects:
                c.execute(
                    "INSERT INTO trending_projects (report_id,name,full_name,url,description,language,stars,forks,today_stars,recommendation,integration_idea,category,scanned_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (report.scan_id, proj.name, proj.full_name, proj.url, proj.description,
                     proj.language, proj.stars, proj.forks, proj.today_stars,
                     proj.recommendation, proj.integration_idea, proj.category, proj.scanned_at)
                )
            for upd in report.tracked_updates:
                c.execute(
                    "INSERT INTO tracked_repos (report_id,repo,category,latest_release,release_url,release_date,changelog,has_breaking,needs_attention) VALUES (?,?,?,?,?,?,?,?,?)",
                    (report.scan_id, upd.repo, upd.category, upd.latest_release,
                     upd.release_url, upd.release_date, upd.changelog,
                     1 if upd.has_breaking else 0, 1 if upd.needs_attention else 0)
                )

    def get_reports(self, limit=20):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM scan_reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_report(self, report_id: str):
        with self._conn() as c:
            r = c.execute("SELECT * FROM scan_reports WHERE id=?", (report_id,)).fetchone()
            if not r:
                return None
            report = dict(r)
            report["dependency_updates"] = [dict(x) for x in c.execute(
                "SELECT * FROM dependency_updates WHERE report_id=?", (report_id,)).fetchall()]
            report["trending_projects"] = [dict(x) for x in c.execute(
                "SELECT * FROM trending_projects WHERE report_id=? ORDER BY stars DESC", (report_id,)).fetchall()]
            report["tracked_updates"] = [dict(x) for x in c.execute(
                "SELECT * FROM tracked_repos WHERE report_id=?", (report_id,)).fetchall()]
            return report

    def get_latest_trending(self, limit=30):
        with self._conn() as c:
            rows = c.execute("""
                SELECT * FROM trending_projects t
                WHERE t.id IN (
                    SELECT MAX(id) FROM trending_projects GROUP BY full_name
                )
                ORDER BY stars DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self):
        with self._conn() as c:
            total_scans = c.execute("SELECT COUNT(*) FROM scan_reports").fetchone()[0]
            successful = c.execute("SELECT COUNT(*) FROM scan_reports WHERE status='completed'").fetchone()[0]
            total_deps = c.execute("SELECT COUNT(DISTINCT package) FROM dependency_updates").fetchone()[0]
            critical_updates = c.execute("SELECT COUNT(*) FROM dependency_updates WHERE level='critical'").fetchone()[0]
            total_trending = c.execute("SELECT COUNT(DISTINCT full_name) FROM trending_projects").fetchone()[0]
            tracked_count = c.execute("SELECT COUNT(DISTINCT repo) FROM tracked_repos").fetchone()[0]
            last_scan = c.execute("SELECT started_at FROM scan_reports ORDER BY created_at DESC LIMIT 1").fetchone()
            return {
                "total_scans": total_scans,
                "successful_scans": successful,
                "total_dependencies_tracked": total_deps,
                "critical_updates": critical_updates,
                "total_trending_discovered": total_trending,
                "tracked_repos": tracked_count,
                "last_scan": last_scan[0] if last_scan else None,
            }


class GitHubScannerEngine:
    """GitHub智能扫描引擎"""

    def __init__(self, store: GitHubScannerStore = None):
        self.store = store or GitHubScannerStore()
        self._github_token = os.environ.get("GITHUB_TOKEN", "")
        self._headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AUTO-EVO-AI-V0.1-GitHub-Scanner",
        }
        if self._github_token:
            self._headers["Authorization"] = f"Bearer {self._github_token}"

    def _make_scan_id(self, scan_type: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw = f"{scan_type}_{ts}"
        return hashlib.md5(raw.encode()).hexdigest()[:12] + f"_{ts}"

    async def _fetch_json(self, url: str, timeout: int = 15) -> Optional[dict]:
        """安全获取JSON"""
        try:
            import httpx
            async with httpx.AsyncClient(headers=self._headers, timeout=timeout, follow_redirects=True) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 403:
                    return {"_rate_limited": True, "_reset": r.headers.get("X-RateLimit-Reset")}
                else:
                    logger.warning(f"GitHub API {r.status_code}: {url}")
                    return None
        except Exception as e:
            logger.warning(f"Fetch failed {url}: {e}")
            return None

    # ─── 依赖更新扫描 ───

    async def scan_dependencies(self) -> list:
        """扫描所有已集成依赖的最新版本"""
        updates = []
        tasks = []
        for pkg, info in INTEGRATED_DEPS.items():
            pypi_name = info.get("pypi", pkg)
            tasks.append(self._check_pypi_version(pkg, pypi_name, info))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, DependencyUpdate):
                updates.append(r)
            elif isinstance(r, Exception):
                logger.warning(f"Dep scan error: {r}")

        updates.sort(key=lambda x: 0 if x.level == "critical" else (1 if x.critical else 2))
        return updates

    async def _check_pypi_version(self, package: str, pypi_name: str, info: dict) -> DependencyUpdate:
        """查PyPI最新版本"""
        import httpx
        installed = info.get("installed") or "unknown"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"https://pypi.org/pypi/{pypi_name}/json")
                if r.status_code != 200:
                    return DependencyUpdate(
                        package=package, installed_version=installed, latest_version="unknown",
                        category=info["category"], critical=info.get("critical", False),
                        level="info", notes="PyPI不可达"
                    )
                data = r.json()
                latest = data["info"]["version"]
                releases = data.get("releases", {})
                changelog_url = f"https://pypi.org/project/{pypi_name}/{latest}/#history"
                publish_date = ""

                # 获取发布日期
                if latest in releases and releases[latest]:
                    first = min(releases[latest], key=lambda x: x.get("upload_time", ""))
                    publish_date = first.get("upload_time", "")[:10]

                # 评估更新级别
                level = self._assess_update_level(installed, latest, info.get("critical", False))

                notes = ""
                if installed != "unknown" and installed != latest:
                    notes = f"可从 {installed} 升级到 {latest}"

                return DependencyUpdate(
                    package=package, installed_version=installed, latest_version=latest,
                    category=info["category"], critical=info.get("critical", False),
                    level=level, changelog_url=changelog_url, publish_date=publish_date, notes=notes
                )
        except Exception as e:
            return DependencyUpdate(
                package=package, installed_version=installed, latest_version="error",
                category=info["category"], critical=info.get("critical", False),
                level="info", notes=str(e)
            )

    def _assess_update_level(self, installed: str, latest: str, critical: bool) -> str:
        """评估更新紧迫程度"""
        if installed == "unknown":
            return "info"
        if installed == latest:
            return "info"
        if critical:
            return "high"
        # 比较版本号
        try:
            i_parts = [int(x) for x in re.split(r'[.\-]', installed) if x.isdigit()][:2]
            l_parts = [int(x) for x in re.split(r'[.\-]', latest) if x.isdigit()][:2]
            if len(i_parts) >= 1 and len(l_parts) >= 1:
                if l_parts[0] > i_parts[0]:
                    return "high"   # 大版本升级
                if l_parts[0] == i_parts[0] and len(l_parts) >= 2 and l_parts[1] > i_parts[1]:
                    return "medium"  # 小版本升级
            return "low"
        except (ValueError, IndexError, TypeError):
            return "low"

    # ─── GitHub Trending 扫描 ───

    async def scan_trending(self) -> list:
        """扫描GitHub Trending Python项目"""
        projects = []
        for lang in ["python", ""]:
            for since in ["daily", "weekly"]:
                url = f"https://api.github.com/search/repositories"
                params = {
                    "q": f"language:python created:>{(datetime.now() - timedelta(days=30 if since == 'daily' else 90)).strftime('%Y-%m-%d')} stars:>50",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 30,
                }
                data = await self._fetch_json(f"{url}?" + "&".join(f"{k}={v}" for k, v in params.items()))
                if not data or "items" not in data:
                    continue
                for item in data["items"]:
                    proj = self._parse_trending_item(item, since)
                    if proj:
                        projects.append(proj)
        # 去重
        seen = set()
        unique = []
        for p in projects:
            if p.full_name not in seen:
                seen.add(p.full_name)
                unique.append(p)
        unique.sort(key=lambda x: x.stars, reverse=True)
        return unique[:50]

    def _parse_trending_item(self, item: dict, since: str) -> Optional[TrendingProject]:
        """解析Trending项目"""
        desc = item.get("description") or ""
        topics = item.get("topics") or []
        full_name = item.get("full_name", "")
        # 过滤已集成的
        if full_name in TRACKED_REPOS:
            return None
        # 评估推荐级别
        stars = item.get("stargazers_count", 0)
        forks = item.get("forks_count", 0)
        rec, idea = self._evaluate_project(full_name, desc, topics, stars, forks)

        return TrendingProject(
            name=item.get("name", ""),
            full_name=full_name,
            url=item.get("html_url", ""),
            description=desc[:200],
            language=item.get("language", "") or "Python",
            stars=stars,
            forks=forks,
            recommendation=rec,
            integration_idea=idea,
            category=self._categorize_project(desc, topics),
            scanned_at=datetime.now().isoformat(),
        )

    def _evaluate_project(self, full_name: str, desc: str, topics: list, stars: int, forks: int) -> tuple:
        """评估项目推荐级别和集成想法"""
        text = f"{full_name} {desc} {' '.join(topics)}".lower()

        # 高相关性关键词
        high_relevance = ["agent", "llm", "automation", "workflow", "fastapi", "api-gateway",
                          "monitoring", "observability", "rag", "vector", "embedding",
                          "pipeline", "orchestr", "scheduler", "task-queue", "dashboard"]
        medium_relevance = ["python", "tool", "framework", "library", "sdk", "cli",
                            "security", "auth", "database", "cache", "deploy"]

        high_hits = sum(1 for kw in high_relevance if kw in text)
        med_hits = sum(1 for kw in medium_relevance if kw in text)

        # 推荐级别
        if high_hits >= 2 and stars > 1000:
            level = "high"
        elif high_hits >= 1 or med_hits >= 3:
            level = "medium"
        else:
            level = "low"

        # 集成想法
        ideas = []
        if any(kw in text for kw in ["agent", "llm"]):
            ideas.append("可作为AI模块增强")
        if any(kw in text for kw in ["monitoring", "observability"]):
            ideas.append("可增强系统监控能力")
        if any(kw in text for kw in ["pipeline", "workflow", "orchestr"]):
            ideas.append("可增强管线编排引擎")
        if any(kw in text for kw in ["security", "auth"]):
            ideas.append("可增强安全模块")
        if any(kw in text for kw in ["vector", "rag", "embedding"]):
            ideas.append("可增强向量搜索和RAG能力")
        if any(kw in text for kw in ["fastapi", "api"]):
            ideas.append("可参考优化API层")
        if any(kw in text for kw in ["scheduler", "task-queue"]):
            ideas.append("可增强任务调度")
        if any(kw in text for kw in ["dashboard", "ui"]):
            ideas.append("可参考优化Dashboard")

        idea = " | ".join(ideas[:3]) if ideas else "关注中"
        return level, idea

    def _categorize_project(self, desc: str, topics: list) -> str:
        """分类项目"""
        text = f"{desc} {' '.join(topics)}".lower()
        cats = {
            "AI/ML": ["ai", "ml", "llm", "gpt", "model", "neural", "deep-learning", "nlp", "rag", "embedding", "agent"],
            "Web框架": ["fastapi", "flask", "django", "api", "web", "http", "server", "asgi"],
            "数据处理": ["data", "etl", "pipeline", "stream", "analytics", "pandas"],
            "DevOps": ["docker", "kubernetes", "ci", "cd", "deploy", "infra", "terraform"],
            "安全": ["security", "auth", "encrypt", "firewall", "audit", "vuln"],
            "监控": ["monitor", "observ", "metric", "alert", "log", "trace", "prometheus", "grafana"],
            "数据库": ["database", "sql", "redis", "postgres", "mongo", "vector", "chroma"],
            "自动化": ["automation", "workflow", "orchestr", "scheduler", "task", "cron"],
            "工具": ["cli", "tool", "util", "sdk", "library"],
        }
        for cat, keywords in cats.items():
            if any(kw in text for kw in keywords):
                return cat
        return "其他"

    # ─── 关注仓库更新 ───

    async def scan_tracked_repos(self) -> list:
        """扫描关注仓库的最新release"""
        updates = []
        for repo, info in TRACKED_REPOS.items():
            upd = await self._check_repo_release(repo, info)
            if upd:
                updates.append(upd)
        # 延迟避免GitHub限流
        await asyncio.sleep(1)
        return updates

    async def _check_repo_release(self, repo: str, info: dict) -> Optional[TrackedRepoUpdate]:
        """查GitHub Release"""
        data = await self._fetch_json(f"https://api.github.com/repos/{repo}/releases/latest")
        if not data or "tag_name" not in data:
            return None

        tag = data["tag_name"]
        url = data.get("html_url", "")
        date = data.get("published_at", "")[:10] if data.get("published_at") else ""
        body = (data.get("body") or "")[:500]

        # 检测Breaking Changes
        breaking = any(kw in body.lower() for kw in
                       ["breaking", "removed", "deprecated", "incompatible", "migration"])

        return TrackedRepoUpdate(
            repo=repo, category=info["category"],
            latest_release=tag, release_url=url, release_date=date,
            changelog=body, has_breaking=breaking,
            needs_attention=breaking or info["category"] == "web"
        )

    # ─── 完整扫描 ───

    async def run_scan(self, scan_type: str = "full") -> ScanReport:
        """执行扫描"""
        scan_id = self._make_scan_id(scan_type)
        report = ScanReport(
            scan_id=scan_id,
            scan_type=scan_type,
            started_at=datetime.now().isoformat(),
        )

        logger.info(f"[GitHubScanner] 开始扫描: {scan_type} (id={scan_id})")

        try:
            if scan_type in ("dependency", "full"):
                report.dependency_updates = await self.scan_dependencies()
                logger.info(f"[GitHubScanner] 依赖扫描完成: {len(report.dependency_updates)}个更新")

            if scan_type in ("trending", "full"):
                report.trending_projects = await self.scan_trending()
                logger.info(f"[GitHubScanner] Trending扫描完成: {len(report.trending_projects)}个项目")

            if scan_type in ("tracked", "full"):
                report.tracked_updates = await self.scan_tracked_repos()
                logger.info(f"[GitHubScanner] 关注仓库扫描完成: {len(report.tracked_updates)}个更新")

            report.status = "completed"
            report.summary = {
                "dependency_updates": len(report.dependency_updates),
                "trending_projects": len(report.trending_projects),
                "tracked_updates": len(report.tracked_updates),
                "critical_deps": sum(1 for d in report.dependency_updates if d.level in ("critical", "high")),
                "high_recommendations": sum(1 for t in report.trending_projects if t.recommendation == "high"),
                "breaking_changes": sum(1 for t in report.tracked_updates if t.has_breaking),
            }

        except Exception as e:
            report.status = "failed"
            report.errors.append(str(e))
            logger.error(f"[GitHubScanner] 扫描失败: {e}")

        report.finished_at = datetime.now().isoformat()
        report.duration_ms = int((datetime.fromisoformat(report.finished_at) -
                                  datetime.fromisoformat(report.started_at)).total_seconds() * 1000)

        # 持久化
        self.store.save_report(report)
        logger.info(f"[GitHubScanner] 扫描完成: {report.status} ({report.duration_ms}ms)")

        return report

    def get_stats(self) -> dict:
        return self.store.get_stats()

    def get_reports(self, limit=20) -> list:
        return self.store.get_reports(limit)

    def get_report(self, report_id: str) -> Optional[dict]:
        return self.store.get_report(report_id)

    def get_latest_trending(self, limit=30) -> list:
        return self.store.get_latest_trending(limit)


# ─── 单例 + 包装方法 ───
_gh_instance = None

def get_github_scanner() -> "GitHubScannerEngine":
    global _gh_instance
    if _gh_instance is None:
        _gh_instance = GitHubScannerEngine()
    return _gh_instance
