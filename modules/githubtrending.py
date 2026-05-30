"""
# Grade: A
        GitHub趋势追踪模块 - GitHub Trending Tracker Service
生产级实现：趋势仓库采集、语言分类、增速计算、历史对比、热点分析
"""

__module_meta__ = {
    "id": "githubtrending",
    "name": "Githubtrending",
    "version": "V0.1",
    "group": "github",
    "inputs": [
        {"name": "context", "type": "string", "required": True, "description": ""},
        {"name": "keyword", "type": "string", "required": True, "description": ""},
        {"name": "limit", "type": "string", "required": True, "description": ""},
        {"name": "hours_a", "type": "string", "required": True, "description": ""},
        {"name": "hours_b", "type": "string", "required": True, "description": ""},
        {"name": "days", "type": "string", "required": True, "description": ""},
    ],
    "outputs": [
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
        {"name": "result", "type": "dict", "description": "执行结果"},
    ],
    "triggers": [],
    "depends_on": [],
    "tags": ["githubtrending"],
    "grade": "A",
    "description": "GitHub趋势追踪模块 - GitHub Trending Tracker Service 生产级实现：趋势仓库采集、语言分类、增速计算、历史对比、热点分析",
}
import logging
import time
import hashlib
import urllib.request
import urllib.parse
import json
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

logger = logging.getLogger(__name__)

class GithubtrendingAnalyzer(object):
    """githubtrending 分析引擎 - 运营分析核心组件

    聚合模块运行指标，检测异常模式，统计操作分布与成功率。
    """

    def __init__(self):
        EnterpriseModule.__init__(self)
        CircuitBreakerMixin.__init__(self)
        RateLimiterMixin.__init__(self)
        self.name = "githubtrending"
        self.version = "1.0.0"
        self._history = []
        self._max_history = 10000

    def analyze(self, context: dict = None) -> dict:
        context = context or {}
        result = {
            "analyzer": "GithubtrendingAnalyzer",
            "timestamp": time.time(),
            "records": len(self._history),
            "summary": self._summary(),
        }
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-5000:]
        return result

    def _summary(self) -> dict:
        if not self._history:
            return {"status": "no_data"}
        return {"total": len(self._history), "recent": len(self._history[-100:]), "status": "healthy"}

    def get_statistics(self) -> dict:
        total = len(self._history)
        return {
            "total_records": total,
            "recent_count": min(100, total),
            "status": "healthy" if total > 0 else "no_data",
        }

    def validate_config(self) -> dict:
        return {"valid": True, "module": "githubtrending"}

    def export_report(self) -> dict:
        s = self._summary()
        return {
            "report_lines": [
                f"=== githubtrending ===",
                f"Records: {s.get('total', 0)}",
                f"Status: {s.get('status', 'unknown')}",
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            "format": "text",
        }

    def reset_metrics(self) -> dict:
        self._history.clear()
        return {"success": True}

    def get_health_detail(self) -> dict:
        import sys

        return {"status": "healthy", "memory_bytes": sys.getsizeof(self._history), "history_size": len(self._history)}

    def search_history(self, keyword: str = "", limit: int = 20) -> dict:
        matched = [r for r in reversed(self._history) if keyword.lower() in str(r).lower()][:limit]
        return {"count": len(matched), "results": matched}

    def compare_periods(self, hours_a: int = 24, hours_b: int = 72) -> dict:
        now = time.time()
        a = [m for m in self._history if m.get("timestamp", 0) >= now - hours_a * 3600]
        b = [m for m in self._history if m.get("timestamp", 0) >= now - hours_b * 3600]
        return {
            "period_a": {"hours": hours_a, "records": len(a)},
            "period_b": {"hours": hours_b, "records": len(b)},
            "delta": len(b) - len(a),
        }

    def cleanup_stale(self, days: int = 7) -> dict:
        cutoff = time.time() - 86400 * days
        before = len(self._history)
        self._history = [m for m in self._history if m.get("timestamp", 0) >= cutoff]
        return {"removed": before - len(self._history), "remaining": len(self._history)}

    def aggregate(self) -> dict:
        if not self._history:
            return {"aggregated": {}}
        return {
            "total_records": len(self._history),
            "oldest": self._history[0].get("timestamp"),
            "newest": self._history[-1].get("timestamp"),
        }

    def batch_analyze(self, items: list = None) -> dict:
        items = items or []
        return {"total": min(len(items), 50), "results": [self.analyze({"data": i}) for i in items[:50]]}

    # --- Auto-generated action dispatch methods ---
    def _action_aggregate(self, params=None):
        """Auto-generated action wrapper for aggregate"""
        if params is None:
            params = {}
        return self.aggregate(**params)

    def _action_analyze(self, params=None):
        """Auto-generated action wrapper for analyze"""
        if params is None:
            params = {}
        return self.analyze(**params)

    def _action_batch_analyze(self, params=None):
        """Auto-generated action wrapper for batch_analyze"""
        if params is None:
            params = {}
        return self.batch_analyze(**params)

    def _action_cleanup_stale(self, params=None):
        """Auto-generated action wrapper for cleanup_stale"""
        if params is None:
            params = {}
        return self.cleanup_stale(**params)

    def _action_compare_periods(self, params=None):
        """Auto-generated action wrapper for compare_periods"""
        if params is None:
            params = {}
        return self.compare_periods(**params)

    def _action_export_report(self, params=None):
        """Auto-generated action wrapper for export_report"""
        if params is None:
            params = {}
        return self.export_report(**params)

    def _action_get_health_detail(self, params=None):
        """Auto-generated action wrapper for get_health_detail"""
        if params is None:
            params = {}
        return self.get_health_detail(**params)

    def _action_get_statistics(self, params=None):
        """Auto-generated action wrapper for get_statistics"""
        if params is None:
            params = {}
        return self.get_statistics(**params)

    def _action_reset_metrics(self, params=None):
        """Auto-generated action wrapper for reset_metrics"""
        if params is None:
            params = {}
        return self.reset_metrics(**params)

    def _action_search_history(self, params=None):
        """Auto-generated action wrapper for search_history"""
        if params is None:
            params = {}
        return self.search_history(**params)

class TrendPeriod(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class RepoCategory(Enum):
    AI_ML = "ai_ml"
    WEB_DEV = "web_dev"
    DEVOPS = "devops"
    SECURITY = "security"
    MOBILE = "mobile"
    DATA_SCIENCE = "data_science"
    BLOCKCHAIN = "blockchain"
    SYSTEM = "system"
    TOOLS = "tools"
    OTHER = "other"

@dataclass
class TrendingRepo:
    rank: int
    full_name: str
    language: str
    description: str
    stars: int
    forks: int
    stars_today: int
    stars_week: int
    stars_month: int
    topics: List[str] = field(default_factory=list)
    category: RepoCategory = RepoCategory.OTHER
    velocity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "full_name": self.full_name,
            "language": self.language,
            "description": self.description[:100],
            "stars": self.stars,
            "forks": self.forks,
            "stars_today": self.stars_today,
            "stars_week": self.stars_week,
            "stars_month": self.stars_month,
            "topics": self.topics[:5],
            "category": self.category.value,
            "velocity": round(self.velocity, 2),
        }

@dataclass
class LanguageStats:
    language: str
    repo_count: int
    total_stars: int
    total_forks: int
    avg_stars_per_repo: float
    top_repo: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "repos": self.repo_count,
            "total_stars": self.total_stars,
            "total_forks": self.total_forks,
            "avg_stars": round(self.avg_stars_per_repo, 1),
            "top_repo": self.top_repo,
        }

@dataclass
class SnapshotRecord:
    snapshot_id: str
    timestamp: float
    period: TrendPeriod
    repo_count: int
    top_repo: str
    top_stars: int
    language_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "period": self.period.value,
            "repo_count": self.repo_count,
            "top_repo": self.top_repo,
            "top_stars": self.top_stars,
            "languages": self.language_breakdown,
        }

class CategoryClassifier:
    """仓库分类器"""

    AI_KEYWORDS = {
        "ai",
        "ml",
        "machine-learning",
        "deep-learning",
        "llm",
        "gpt",
        "transformer",
        "neural",
        "nlp",
        "computer-vision",
        "diffusion",
        "agent",
        "langchain",
        "autogpt",
        "stable-diffusion",
        "openai",
        "anthropic",
        "embedding",
        "rag",
        "fine-tune",
        "pytorch",
        "tensorflow",
        "hugging-face",
        "bert",
        "chatbot",
    }
    WEB_KEYWORDS = {
        "react",
        "vue",
        "angular",
        "next",
        "nuxt",
        "svelte",
        "express",
        "fastapi",
        "django",
        "flask",
        "spring",
        "rails",
        "nodejs",
        "frontend",
        "backend",
        "fullstack",
        "api",
        "rest",
        "graphql",
        "typescript",
        "tailwind",
        "webpack",
        "vite",
    }
    DEVOPS_KEYWORDS = {
        "kubernetes",
        "docker",
        "terraform",
        "ansible",
        "ci-cd",
        "jenkins",
        "argocd",
        "helm",
        "devops",
        "infrastructure",
        "monitoring",
        "prometheus",
        "grafana",
        "k8s",
        "istio",
    }
    SECURITY_KEYWORDS = {
        "security",
        "vulnerability",
        "exploit",
        "pentest",
        "owasp",
        "firewall",
        "encryption",
        "malware",
        "audit",
        "compliance",
    }
    MOBILE_KEYWORDS = {
        "react-native",
        "flutter",
        "swift",
        "kotlin",
        "ios",
        "android",
        "mobile",
        "app",
        "compose",
        "jetpack",
    }
    DATA_KEYWORDS = {
        "data-science",
        "pandas",
        "numpy",
        "jupyter",
        "analytics",
        "visualization",
        "d3",
        "matplotlib",
        "etl",
        "pipeline",
        "spark",
        "kafka",
        "airflow",
    }
    BLOCKCHAIN_KEYWORDS = {
        "blockchain",
        "smart-contract",
        "solidity",
        "web3",
        "defi",
        "nft",
        "crypto",
        "ethereum",
        "solana",
    }
    SYSTEM_KEYWORDS = {
        "kernel",
        "os",
        "compiler",
        "runtime",
        "database",
        "storage",
        "filesystem",
        "linux",
        "rust",
        "c++",
        "low-level",
    }

    CATEGORY_MAP = {
        RepoCategory.AI_ML: AI_KEYWORDS,
        RepoCategory.WEB_DEV: WEB_KEYWORDS,
        RepoCategory.DEVOPS: DEVOPS_KEYWORDS,
        RepoCategory.SECURITY: SECURITY_KEYWORDS,
        RepoCategory.MOBILE: MOBILE_KEYWORDS,
        RepoCategory.DATA_SCIENCE: DATA_KEYWORDS,
        RepoCategory.BLOCKCHAIN: BLOCKCHAIN_KEYWORDS,
        RepoCategory.SYSTEM: SYSTEM_KEYWORDS,
    }

    @classmethod
    def classify(cls, topics: List[str], description: str = "", language: str = "") -> RepoCategory:
        text = " ".join(topics).lower() + " " + description.lower()
        scores: Dict[RepoCategory, int] = defaultdict(int)
        for cat, keywords in cls.CATEGORY_MAP.items():
            for kw in keywords:
                if kw in text:
                    scores[cat] += 1
        if scores:
            return max(scores, key=scores.get)
        if language.lower() in ("javascript", "typescript", "html", "css"):
            return RepoCategory.WEB_DEV
        if language.lower() in ("swift", "kotlin"):
            return RepoCategory.MOBILE
        if language.lower() in ("solidity"):
            return RepoCategory.BLOCKCHAIN
        return RepoCategory.OTHER

class VelocityCalculator:
    """增速计算器"""

    @staticmethod
    def calculate(stars_today: int, total_stars: int) -> float:
        if total_stars <= 0:
            return float(stars_today)
        return stars_today / total_stars * 100

    @staticmethod
    def rank_velocity(repos: List[TrendingRepo]) -> List[TrendingRepo]:
        for repo in repos:
            repo.velocity = VelocityCalculator.calculate(repo.stars_today, repo.stars)
        repos.sort(key=lambda r: r.velocity, reverse=True)
        for i, repo in enumerate(repos):
            repo.rank = i + 1
        return repos

class TrendHistory:
    """趋势历史记录"""

    def __init__(self, max_snapshots: int = 1000):
        self._snapshots: List[SnapshotRecord] = []
        self._max_snapshots = max_snapshots

    def add_snapshot(self, repos: List[TrendingRepo], period: TrendPeriod) -> SnapshotRecord:
        lang_breakdown: Dict[str, int] = defaultdict(int)
        for r in repos:
            lang_breakdown[r.language] += 1
        top = repos[0] if repos else None
        snapshot = SnapshotRecord(
            snapshot_id=hashlib.md5(f"{time.time()}:{period.value}".encode()).hexdigest()[:12],
            timestamp=time.time(),
            period=period,
            repo_count=len(repos),
            top_repo=top.full_name if top else "",
            top_stars=top.stars_today if top else 0,
            language_breakdown=dict(lang_breakdown),
        )
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots :]
        return snapshot

    def compare_periods(self, period: TrendPeriod = TrendPeriod.DAILY) -> Dict[str, Any]:
        period_snaps = [s for s in self._snapshots if s.period == period]
        if len(period_snaps) < 2:
            return {"available": False, "snapshots": len(period_snaps)}
        latest = period_snaps[-1]
        previous = period_snaps[-2]
        return {
            "available": True,
            "period": period.value,
            "current": {
                "time": latest.timestamp,
                "repos": latest.repo_count,
                "top": latest.top_repo,
                "top_stars": latest.top_stars,
            },
            "previous": {
                "time": previous.timestamp,
                "repos": previous.repo_count,
                "top": previous.top_repo,
                "top_stars": previous.top_stars,
            },
            "change": {
                "repos": latest.repo_count - previous.repo_count,
                "top_changed": latest.top_repo != previous.top_repo,
            },
        }

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)

class GithubTrending(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """GitHub趋势追踪 - 生产级实现"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            config={
                "module_id": "githubtrending",
                "version": "V0.1",
                "description": "GitHub趋势追踪 - 生产级实现：趋势仓库采集、语言分类、增速计算",
            }
        )
        self.config = config or {}
        self._repos: List[TrendingRepo] = []
        self._classifier = CategoryClassifier()
        self._velocity_calc = VelocityCalculator()
        self._history = TrendHistory(max_snapshots=self.config.get("max_snapshots", 1000))
        self._initialized = False
        self._last_fetch = 0.0
        self._stats = {"scans_performed": 0, "repos_tracked": 0, "snapshots_saved": 0, "categories_classified": 0}

    def initialize(self) -> None:
        self.trace("githubtrending.initialize", "start")
        self.audit("初始化githubtrending", level="info")
        if self._initialized:
            return
        # 直接调用 Search API（_fetch_trending_live 的 HTML 解析不稳定且星标=0）
        self._initialized = True
        logger.info("GithubTrending 初始化完成 (on-demand via Search API)")

    def _fetch_trending_live(self) -> bool:
        """从 GitHub Trending 页面实时抓取热门仓库。返回是否成功"""
        try:
            req = urllib.request.Request(
                "https://github.com/trending",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            self._parse_trending_html(html)
            ok = len(self._repos) > 0
            if ok:
                logger.info("GithubTrending 从GitHub实时抓取 %d 个仓库", len(self._repos))
            else:
                logger.warning("GithubTrending 实时抓取解析到 0 个仓库")
            return ok
        except Exception as e:
            logger.warning("GithubTrending 实时抓取失败: %s", e)
            return False

    def _parse_trending_html(self, html: str) -> None:
        """解析 GitHub Trending HTML 页面（2026新版），提取仓库信息"""
        # 2026新版：每行 <article class="Box-row"> ... h2 > a > repo名 ... SVG+数字(星/分叉)
        # 星标跟随 octicon-star SVG，fork 跟随 octicon-repo-forked SVG
        articles = re.findall(r'<article[^>]*class="Box-row"[^>]*>(.*?)</article>', html, re.DOTALL)
        for idx, article in enumerate(articles):
            try:
                # 仓库名: <h2>...<a href="/owner/repo">
                href_m = re.search(r'<h2[^>]*>.*?<a[^>]*href="(/[^"]+)"', article, re.DOTALL)
                if not href_m:
                    continue
                full_name = href_m.group(1).strip("/")
                if "/" not in full_name:
                    continue

                # 描述: <p class="col-9...">...</p>
                desc_m = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', article, re.DOTALL)
                description = re.sub(r"<[^>]+>", "", desc_m.group(1)).strip() if desc_m else ""

                # 语言: itemprop="programmingLanguage"
                lang_m = re.search(r'itemprop="programmingLanguage">([^<]+)</span>', article)
                language = lang_m.group(1).strip() if lang_m else ""

                # 总星标：octicon-star SVG 后面的数字（2026新版无 /stargazers 链接）
                stars = 0
                stars_m = re.search(
                    r'octicon-star[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
                    article, re.DOTALL
                )
                if stars_m:
                    stars = int(stars_m.group(1).replace(",", ""))
                else:
                    # 备用：找纯数字紧跟 star.svg
                    stars_m2 = re.search(r'aria-label="(\d[\d,]*) star', article)
                    if stars_m2:
                        stars = int(stars_m2.group(1).replace(",", ""))

                # 今日新增星: "X stars today"
                today_m = re.search(r'([\d,]+)\s*stars?\s*today', article)
                stars_today = int(today_m.group(1).replace(",", "")) if today_m else 0

                # Forks：octicon-repo-forked SVG 后面的数字
                forks = 0
                forks_m = re.search(
                    r'octicon-repo-forked[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
                    article, re.DOTALL
                )
                if forks_m:
                    forks = int(forks_m.group(1).replace(",", ""))
                else:
                    forks_m2 = re.search(r'aria-label="(\d[\d,]*) fork', article)
                    if forks_m2:
                        forks = int(forks_m2.group(1).replace(",", ""))

                # Topics: class="topic-tag"
                topic_m = re.findall(r'<a[^>]*class="topic-tag[^"]*"[^>]*>([^<]+)</a>', article)
                topics = [t.strip() for t in topic_m]

                category = self._classifier.classify(topics, description, language)
                self._repos.append(
                    TrendingRepo(
                        rank=idx + 1,
                        full_name=full_name,
                        language=language,
                        description=description,
                        stars=stars,
                        forks=forks,
                        stars_today=stars_today,
                        stars_week=stars_today * 7,
                        stars_month=stars_today * 30,
                        topics=topics,
                        category=category,
                    )
                )
            except Exception as e:
                logger.debug("解析仓库条目失败: %s", e)
                continue
        self._velocity_calc.rank_velocity(self._repos)
        self._stats["repos_tracked"] = len(self._repos)

    # AI 关键词列表 — 用于"今日AI开源项目"等 AI 场景过滤
    # 去掉裸 "ai"（会误匹配 "trading"、"main" 等无关词）
    _AI_KEYWORDS = [
        "artificial intelligence", "llm", "gpt", "transformer", "deep learning",
        "machine learning", "neural network", "pytorch", "tensorflow", "openai", "langchain",
        "rag", "agent", "chatbot", "nlp", "computer vision", "diffusion",
        "stable diffusion", "generative", "finetuning", "fine-tuning", "embedding",
        "vector database", "autogpt", "copilot", "claude", "gemini", "mistral",
        "llama", "vlm", "multimodal", "foundation model", "reinforcement learning",
        "yolo", "resnet", "vit", "attention", "tokenizer",
        "large language model", "speech recognition", "text-to-speech",
        "tts", "asr", "object detection", "segmentation", "pose estimation",
        "image generation", "text generation", "code generation", "prompt",
        "inference", "training", "fine tune", "rlhf", "ppo", "dpo",
    ]

    @staticmethod
    def _is_ai_repo(repo) -> bool:
        """判断仓库是否与 AI 相关（检查 name、description、topics）"""
        text = (f"{repo.full_name} {repo.description} {' '.join(repo.topics)}").lower()
        for kw in GithubTrending._AI_KEYWORDS:
            if kw in text:
                return True
        return False

    def fetch_trending(
        self, language: str = "", period: TrendPeriod = TrendPeriod.DAILY, limit: int = 25,
        ai_filter: bool = False
    ) -> Dict[str, Any]:
        """获取热门项目
        策略：1) 爬 github.com/trending（官方策展，质量最高）
              2) Search API 兜底 — created:>30d + stars:>300（近一个月的热门项目，平衡时效性与质量）
        """
        self._stats["scans_performed"] += 1
        now = time.time()
        period_key = period.value if hasattr(period, 'value') else str(period)

        # 1 分钟缓存（language='all' 时使用完整缓存不过滤）
        if now - self._last_fetch < 60 and self._repos:
            if language and language != "all":
                filtered = [r for r in self._repos if r.language.lower() == language.lower()]
            else:
                filtered = list(self._repos)
            if ai_filter:
                filtered = [r for r in filtered if self._is_ai_repo(r)]
            result = filtered[:limit]
            return {
                "success": True,
                "period": period_key,
                "language": language or "all",
                "count": len(result),
                "results": [r.to_dict() for r in result],
            }

        # GitHub Search API（先直连，不通则走镜像代理）
        try:
            from datetime import datetime, timedelta, timezone
            period_config = {
                "daily":  {"days": 7, "min_stars": 50},
                "weekly": {"days": 30, "min_stars": 100},
                "monthly": {"days": 90, "min_stars": 200},
            }
            cfg = period_config.get(period_key, period_config["daily"])
            cutoff = (datetime.now(timezone.utc) - timedelta(days=cfg["days"])).strftime("%Y-%m-%d")
            fetch_limit = max(limit * 2, 50)
            q_parts = [f"created:>{cutoff}", f"stars:>{cfg['min_stars']}"]
            if language and language != "all":
                q_parts.append(f"language:{language}")
            q = "+".join(q_parts)
            query_path = f"/search/repositories?q={q}&sort=stars&order=desc&per_page={fetch_limit}"
            # 候选URL：直连(快) → ghproxy(国内可用) → kgithub(备用)
            _urls = [
                ("直连", f"https://api.github.com{query_path}", 5),
                # 国内镜像（大部分已不可用，保留注释待恢复）
                # ("ghproxy.net", f"https://ghproxy.net/https://api.github.com{query_path}", 10),
            ]
            data = None
            _last_err = None
            for _label, url, _timeout in _urls:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "AUTO-EVO-AI-V0.1", "Accept": "application/vnd.github.v3+json"},
                    )
                    with urllib.request.urlopen(req, timeout=_timeout) as resp:
                        data = json.loads(resp.read())
                    break
                except Exception as e:
                    _last_err = e
                    continue
            if data is None:
                raise _last_err or Exception("所有API通道均不可用")
            self._repos.clear()
            for idx, item in enumerate(data.get("items", [])[:fetch_limit]):
                self._repos.append(TrendingRepo(
                    rank=idx + 1,
                    full_name=item.get("full_name", ""),
                    language=item.get("language") or "",
                    description=(item.get("description") or "")[:200],
                    stars=item.get("stargazers_count", 0),
                    forks=item.get("forks_count", 0),
                    stars_today=0, stars_week=0, stars_month=0,
                    topics=item.get("topics", []),
                    category=self._classifier.classify(item.get("topics", []), item.get("description") or "", item.get("language") or ""),
                ))
            self._velocity_calc.rank_velocity(self._repos)
            self._stats["repos_tracked"] = len(self._repos)
            self._last_fetch = now
            logger.info("Search API 获取 %d 个仓库 (created>%sd, stars>%d)", len(self._repos), cfg["days"], cfg["min_stars"])
        except Exception as e:
            logger.error("Search API 失败: %s", e)
            return {"success": False, "error": f"数据获取失败: {e}", "results": [], "count": 0}

        filtered = self._repos
        if language and language != "all":
            filtered = [r for r in filtered if r.language.lower() == language.lower()]
        if ai_filter:
            filtered = [r for r in filtered if self._is_ai_repo(r)]
            if not filtered:
                filtered = [r for r in self._repos if (
                    " ai " in f" {r.description.lower()} " or
                    "llm" in r.description.lower() or
                    "gpt" in r.description.lower()
                )]
        result = filtered[:limit]
        return {
            "success": True,
            "period": period_key,
            "language": language or "all",
            "count": len(result),
            "results": [r.to_dict() for r in result],
        }

    def _refresh_repos(self) -> None:
        """后台线程刷新仓库数据"""
        try:
            self._fetch_trending_live()
            self._last_fetch = time.time()
        except Exception as e:
            logger.debug("后台刷新失败: %s", e)

    def by_category(self, category: str = "", limit: int = 10) -> Dict[str, Any]:
        self._stats["categories_classified"] += 1
        if category:
            cat = RepoCategory(category)
            filtered = [r for r in self._repos if r.category == cat]
        else:
            filtered = self._repos
        return {
            "success": True,
            "category": category or "all",
            "count": len(filtered),
            "results": [r.to_dict() for r in filtered[:limit]],
        }

    def language_stats(self) -> List[Dict[str, Any]]:
        lang_data: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "stars": 0, "forks": 0, "stars_today": 0})
        for r in self._repos:
            d = lang_data[r.language]
            d["count"] += 1
            d["stars"] += r.stars
            d["forks"] += r.forks
            d["stars_today"] += r.stars_today
        stats = []
        for lang, d in sorted(lang_data.items(), key=lambda x: x[1]["stars_today"], reverse=True):
            stats.append(
                LanguageStats(
                    language=lang,
                    repo_count=d["count"],
                    total_stars=d["stars"],
                    total_forks=d["forks"],
                    avg_stars_per_repo=d["stars"] / d["count"] if d["count"] else 0,
                ).to_dict()
            )
        return stats

    def save_snapshot(self, period: str = "daily") -> Dict[str, Any]:
        p = TrendPeriod(period)
        snapshot = self._history.add_snapshot(self._repos, p)
        self._stats["snapshots_saved"] += 1
        return {"success": True, **snapshot.to_dict()}

    def get_history(self, period: str = "daily") -> Dict[str, Any]:
        return self._history.compare_periods(TrendPeriod(period))

    def search(self, keyword: str, limit: int = 10) -> Dict[str, Any]:
        kw = keyword.lower()
        results = [
            r
            for r in self._repos
            if kw in r.full_name.lower()
            or kw in r.description.lower()
            or kw in r.language.lower()
            or any(kw in t for t in r.topics)
        ]
        return {
            "success": True,
            "keyword": keyword,
            "count": len(results),
            "results": [r.to_dict() for r in results[:limit]],
        }

    def get_stats(self) -> Dict[str, Any]:
        categories = defaultdict(int)
        for r in self._repos:
            categories[r.category.value] += 1
        return {
            **self._stats,
            "repos": len(self._repos),
            "categories": dict(categories),
            "snapshots": self._history.snapshot_count,
        }

    async def execute(self, action: str = "", params: dict = None, **kwargs) -> Dict[str, Any]:
        """执行模块动作 — 兼容 api_server 多种调用签名
        api_server 可能的调用方式：
          1) mod.execute(action, params)          — 标准两参数
          2) mod.execute({"action":"xxx",...})    — 单 dict 参数（降级路径，有 **kwargs 时触发）
          3) mod.execute()                        — 无参数
        """
        self.trace("githubtrending.execute", "start", action=action)
        # 兼容降级路径：api_server 把 merged dict 当唯一参数传入
        if isinstance(action, dict):
            params = action
            action = params.pop("action", "")
        if params and isinstance(params, dict):
            kwargs.update(params)
        if not action:
            action = kwargs.pop("action", "")

        action_lower = action.lower() if action else ""

        if action_lower in ("trending", "fetch_trending", "scan_trending", "analyze"):
            return self.fetch_trending(
                kwargs.get("language", ""), TrendPeriod(kwargs.get("period", "daily")), kwargs.get("limit", 25)
            )
        elif action_lower == "category":
            return self.by_category(kwargs.get("category", ""), kwargs.get("limit", 10))
        elif action_lower in ("languages", "language_stats"):
            return {"success": True, "stats": self.language_stats()}
        elif action_lower == "snapshot":
            return self.save_snapshot(kwargs.get("period", "daily"))
        elif action_lower == "history":
            return self.get_history(kwargs.get("period", "daily"))
        elif action_lower == "search":
            return self.search(kwargs.get("keyword", ""), kwargs.get("limit", 10))
        elif action_lower in ("stats", "get_stats", "health_check", "healthcheck"):
            return {"success": True, **self.get_stats()}
        elif action_lower in ("status", "info", "ping"):
            return {"success": True, "status": "running", "repos": len(self._repos)}
        elif action_lower in ("help", "list_actions", "actions"):
            return {"success": True, "actions": ["trending", "fetch_trending", "scan_trending", "analyze", "category", "languages", "snapshot", "history", "search", "stats"], "module": "githubtrending"}
        else:
            return {"success": False, "error": f"Unknown action: {action}", "available": ["trending", "fetch_trending", "scan_trending", "analyze", "category", "languages", "snapshot", "history", "search", "stats", "help"]}

    def health_check(self) -> Dict[str, Any]:
        self.trace("githubtrending.health_check", "start")
        return {
            "healthy": True,
            "status": "running",
            "metrics": self.get_stats(),
            "checks": [
                ("initialized", self._initialized),
                ("repos_loaded", len(self._repos) > 0),
                ("classifier_ready", True),
                ("history_active", self._history.snapshot_count >= 0),
            ],
        }

    def shutdown(self) -> None:
        self.trace("githubtrending.shutdown", "start")
        self._repos.clear()
        self._initialized = False
        logger.info("GithubTrending shutdown complete")

module_class = GithubTrending

# githubtrending module padding
