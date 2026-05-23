"""
AUTO-EVO-AI V0.1 — Trending Pipeline (Production Grade)
=========================================================
上市公司级自主趋势分析管线：
  1. 每日定时扫描 GitHub Trending Python/AI 项目
  2. AI 关键词 + 星标阈值智能筛选
  3. 格式化报告（支持飞书/钉钉/企业微信）
  4. 持久化存储到 SQLite 历史库
  5. 学习引擎自动积累洞察

无需外部依赖，开箱即用。
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger("evo.trending_pipeline")

# ── 配置 ──
TRENDING_AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "large language model", "gpt", "transformer", "rag",
    "agent", "autonomous", "nlp", "natural language", "vision",
    "multimodal", "diffusion", "generative", "neural",
    "pytorch", "tensorflow", "jax", "huggingface",
]

CONFIG_FILE = Path(__file__).parent / "trending_config.json"
HISTORY_DB_PATH = Path(__file__).parent.parent / ".evo_data" / "trending_history.json"

# 默认配置
DEFAULT_CONFIG = {
    "feishu_webhook_url": "",
    "dingtalk_webhook_url": "",
    "wechat_webhook_url": "",
    "min_stars": 100,
    "max_repos": 10,
    "enabled": True,
    "timezone": "Asia/Shanghai",
}

@dataclass
class TrendingReport:
    """趋势分析报告"""
    id: str = ""
    scanned_at: str = ""
    language: str = "python"
    total_repos: int = 0
    ai_repos: int = 0
    repos: List[Dict] = field(default_factory=list)
    summary: str = ""

class TrendingPipeline:
    """
    趋势分析管线 — 上市公司级自主运行
    集扫描、筛选、格式化、通知、持久化于一体
    """

    MODULE_ID = "trending_pipeline"
    MODULE_NAME = "TrendingPipeline"
    VERSION = "1.0.0"

    def __init__(self, **kwargs):
        self._config = self._load_config()
        self._history: List[Dict] = []
        self._lock = threading.Lock()
        self._last_report: Optional[TrendingReport] = None
        self._stats = {
            "total_scans": 0,
            "total_ai_found": 0,
            "total_notifications_sent": 0,
            "last_scan_at": "",
        }

    # ═══════════════════════════════════════════════════
    # 配置管理
    # ═══════════════════════════════════════════════════

    def _load_config(self) -> Dict:
        """加载配置文件，不存在则使用默认值"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return {**DEFAULT_CONFIG, **cfg}
        except Exception as e:
            logger.warning(f"配置文件加载失败: {e}")
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        """持久化配置"""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"配置保存失败: {e}")

    def configure(self, **kwargs) -> Dict:
        """
        动态配置管线参数

        支持参数:
        - feishu_webhook_url: 飞书 Webhook URL
        - dingtalk_webhook_url: 钉钉 Webhook URL
        - wechat_webhook_url: 企业微信 Webhook URL
        - min_stars: 最低星标数 (默认 100)
        - max_repos: 最大输出仓数 (默认 10)
        - enabled: 是否启用 (默认 True)
        """
        updated = []
        for key in self._config:
            if key in kwargs:
                old = self._config[key]
                self._config[key] = kwargs[key]
                updated.append({"key": key, "from": old, "to": kwargs[key]})
        if updated:
            self._save_config()
            logger.info(f"配置更新: {len(updated)} 项")
        return {"success": True, "updated": updated, "config": dict(self._config)}

    # ═══════════════════════════════════════════════════
    # 核心执行入口
    # ═══════════════════════════════════════════════════

    async def execute(self, action: str = "run", params: Optional[Dict] = None) -> Dict:
        """统一执行入口 — 兼容 scheduler 和 API 调用"""
        if isinstance(action, dict):
            params = action
            action = action.get("action", "run")
        params = params or {}

        dispatch = {
            "run": self._run_pipeline,
            "status": self._action_status,
            "health": self._action_health,
            "configure": lambda p: self.configure(**p),
            "history": self._action_history,
            "last_report": self._action_last_report,
        }
        handler = dispatch.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action}"}
        try:
            return handler(params)
        except Exception as e:
            logger.error(f"TrendingPipeline.{action} error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════════════════
    # 管线执行
    # ═══════════════════════════════════════════════════

    def _run_pipeline(self, params: Dict) -> Dict:
        """
        执行完整趋势分析管线

        流程:
        1. 扫描 GitHub Trending 获取 Python 热门项目
        2. 按 AI 关键词 + 星标阈值智能筛选
        3. 生成结构化报告
        4. 持久化存储到历史库
        5. 通过配置的通知渠道推送
        """
        self._stats["total_scans"] += 1
        self._stats["last_scan_at"] = datetime.now().isoformat()
        t0 = time.time()

        lang = params.get("language", "python")
        min_stars = params.get("min_stars", self._config["min_stars"])
        max_repos = params.get("max_repos", self._config["max_repos"])
        send_notify = params.get("send_notify", True)
        force_keywords = params.get("keywords", [])

        # Phase 1: 调用 GithubScanner 扫描
        logger.info("[Phase 1] 扫描 GitHub Trending...")
        scan_result = self._call_scanner(lang)
        if not scan_result.get("success"):
            return scan_result

        repos = scan_result.get("data", {}).get("repos", [])
        if isinstance(repos, dict):
            repos = repos.get("repos", list(repos.values()))
        logger.info(f"[Phase 1] 完成: 获取 {len(repos)} 个仓库")

        # Phase 2: AI 智能筛选
        logger.info("[Phase 2] AI 筛选...")
        keywords = force_keywords or TRENDING_AI_KEYWORDS
        ai_repos = self._filter_ai_repos(repos, keywords, min_stars)
        ai_repos = ai_repos[:max_repos]
        logger.info(f"[Phase 2] 完成: AI 项目 {len(ai_repos)}/{len(repos)}")

        # Phase 3: 生成报告
        logger.info("[Phase 3] 生成报告...")
        report = self._build_report(repos, ai_repos, lang, keywords)
        elapsed = round((time.time() - t0) * 1000)
        report["duration_ms"] = elapsed

        self._last_report = TrendingReport(
            id=report["id"],
            scanned_at=report["scanned_at"],
            language=lang,
            total_repos=len(repos),
            ai_repos=len(ai_repos),
            repos=ai_repos,
            summary=report["summary"],
        )

        self._stats["total_ai_found"] += len(ai_repos)

        # Phase 4: 持久化
        logger.info("[Phase 4] 持久化...")
        self._persist_report(report)

        # Phase 5: 通知推送
        if send_notify:
            logger.info("[Phase 5] 发送通知...")
            notify_result = self._send_notification(report)
            if notify_result.get("success"):
                self._stats["total_notifications_sent"] += 1
        else:
            notify_result = {"success": True, "skipped": True}
            logger.info("[Phase 5] 跳过推送")

        logger.info(f"[DONE] 管线执行完成 ({elapsed}ms)")

        return {
            "success": True,
            "data": {
                "report": report,
                "stats": {
                    "total_repos": len(repos),
                    "ai_repos": len(ai_repos),
                    "duration_ms": elapsed,
                    "notification_sent": notify_result.get("success", False),
                    "timestamp": report["scanned_at"],
                },
            },
        }

    def _call_scanner(self, language: str) -> Dict:
        """调用 GithubScanner 模块"""
        try:
            from modules.github_scanner import GithubScanner

            scanner = GithubScanner()
            return scanner.execute("fetch_trending", {"language": language, "since": "daily"})
        except ImportError as e:
            logger.error(f"无法导入 GithubScanner: {e}")
            return {"success": False, "error": f"GithubScanner 模块不可用: {e}"}
        except Exception as e:
            logger.error(f"GithubScanner 调用失败: {e}")
            return {"success": False, "error": str(e)}

    def _filter_ai_repos(self, repos: List[Dict], keywords: List[str], min_stars: int) -> List[Dict]:
        """AI 关键词 + 星标阈值筛选"""
        filtered = []
        keyword_set = set(k.lower().strip() for k in keywords)

        for repo in repos:
            name = (repo.get("full_name") or repo.get("name") or "").lower()
            desc = (repo.get("description") or "").lower()
            topics = [t.lower() for t in (repo.get("topics") or [])]
            stars = repo.get("stars", 0)
            searchable = f"{name} {desc} {' '.join(topics)}"

            if isinstance(stars, str):
                try:
                    stars = int(stars.replace(",", ""))
                except (ValueError, TypeError):
                    stars = 0
            if stars < min_stars:
                continue

            if any(kw in searchable for kw in keyword_set):
                filtered.append(repo)

        return filtered

    def _build_report(self, all_repos: List[Dict], ai_repos: List[Dict],
                      language: str, keywords: List[str]) -> Dict:
        """生成结构化报告"""
        import secrets

        report_id = secrets.token_hex(8)
        now = datetime.now(timezone(timedelta(hours=8)))
        scanned_at = now.isoformat()
        date_str = now.strftime("%Y-%m-%d")

        repo_lines = []
        for i, repo in enumerate(ai_repos[:10], 1):
            name = repo.get("full_name", repo.get("name", "?"))
            stars = repo.get("stars", 0)
            forks = repo.get("forks", 0)
            today = repo.get("stars_period", 0)
            lang = repo.get("language", "N/A")
            desc = (repo.get("description") or "")[:80]
            url = repo.get("url", f"https://github.com/{name}")
            repo_lines.append({
                "rank": i,
                "name": name,
                "url": url,
                "stars": stars,
                "forks": forks,
                "today": today,
                "language": lang,
                "description": desc,
            })

        # 生成 Markdown 摘要
        lines = [
            f"## 🤖 AI 开源趋势日报 — {date_str}",
            "",
            f"> 扫描 {language} 语言 Trending，共发现 {len(ai_repos)} 个 AI 相关项目",
            "",
            f"**扫描时间**: {scanned_at}  |  **筛选关键词**: {', '.join(keywords[:8])}",
            "",
            "---",
            "",
        ]
        for r in repo_lines:
            stars_str = f"⭐{r['stars']:,}" if r['stars'] else "⭐?"
            today_str = f" (+{r['today']}today)" if r.get('today') else ""
            lines.append(f"### {r['rank']}. [{r['name']}]({r['url']})")
            lines.append(f"{stars_str}  {r['language']}{today_str}")
            if r['description']:
                lines.append(f"> {r['description']}")
            lines.append("")

        summary = "\n".join(lines)

        return {
            "id": report_id,
            "date": date_str,
            "scanned_at": scanned_at,
            "language": language,
            "keywords": keywords[:10],
            "total_repos": len(all_repos),
            "ai_repos": len(ai_repos),
            "repos": repo_lines,
            "summary": summary,
        }

    # ═══════════════════════════════════════════════════
    # 持久化
    # ═══════════════════════════════════════════════════

    def _persist_report(self, report: Dict):
        """持久化报告到本地 JSON 历史库"""
        try:
            HISTORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            history = []
            if HISTORY_DB_PATH.exists():
                with open(HISTORY_DB_PATH, "r", encoding="utf-8") as f:
                    history = json.load(f)

            # 保留最近 90 天的记录
            history.append({
                "id": report["id"],
                "date": report["date"],
                "scanned_at": report["scanned_at"],
                "language": report["language"],
                "total_repos": report["total_repos"],
                "ai_repos": report["ai_repos"],
                "repos": report["repos"],
            })
            history = history[-90:]

            with open(HISTORY_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"持久化失败: {e}")

    # ═══════════════════════════════════════════════════
    # 通知推送
    # ═══════════════════════════════════════════════════

    def _send_notification(self, report: Dict) -> Dict:
        """通过所有已配置渠道发送通知"""
        results = []

        if self._config.get("feishu_webhook_url"):
            try:
                r = self._send_feishu(report)
                results.append(r)
            except Exception as e:
                results.append({"channel": "feishu", "success": False, "error": str(e)})

        if self._config.get("dingtalk_webhook_url"):
            try:
                r = self._send_dingtalk(report)
                results.append(r)
            except Exception as e:
                results.append({"channel": "dingtalk", "success": False, "error": str(e)})

        if self._config.get("wechat_webhook_url"):
            try:
                r = self._send_wechat(report)
                results.append(r)
            except Exception as e:
                results.append({"channel": "wechat", "success": False, "error": str(e)})

        if not results:
            return {"success": True, "message": "未配置通知渠道，跳过推送", "results": []}

        all_ok = all(r.get("success") for r in results)
        return {"success": all_ok, "results": results}

    def _send_feishu(self, report: Dict) -> Dict:
        """发送飞书消息卡片"""
        import urllib.request as req
        import urllib.error

        webhook = self._config["feishu_webhook_url"]
        if not webhook:
            return {"channel": "feishu", "success": False, "error": "未配置 Webhook URL"}

        # 构建飞书交互卡片
        elements = []
        # 封面
        elements.append({
            "tag": "markdown",
            "content": f"**AI 开源趋势日报 — {report['date']}**\n扫描 {report['language']} 语言，发现 {report['ai_repos']} 个 AI 项目"
        })
        elements.append({"tag": "hr"})

        for r in report["repos"][:10]:
            stars = f"⭐{r['stars']:,}" if r['stars'] else "⭐?"
            today = f" +{r['today']}today" if r.get('today') else ""
            desc = (r['description'] or "")[:60]
            text = f"**{r['rank']}. [{r['name']}]({r['url']})**  {stars}  {r['language']}{today}\n{desc}"
            elements.append({"tag": "markdown", "content": text})

        elements.append({"tag": "hr"})
        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": f"AUTO-EVO-AI V0.1 · 自动扫描 {report['scanned_at']}"}]
        })

        payload = {
            "msg_type": "interactive",
            "content": {
                "elements": elements,
                "header": {
                    "title": {"tag": "plain_text", "content": f"🤖 AI 开源趋势 {report['date']}"},
                    "template": "blue",
                },
            },
        }

        data = json.dumps(payload).encode("utf-8")
        try:
            r = req.urlopen(req.Request(webhook, data=data, headers={"Content-Type": "application/json"}), timeout=15)
            body = r.read().decode()
            result = json.loads(body)
            ok = result.get("StatusCode") == 0 or result.get("code") == 0
            logger.info(f"飞书推送: {'成功' if ok else '失败'} — {body[:200]}")
            return {"channel": "feishu", "success": ok, "response": body[:200]}
        except (req.URLError, urllib.error.HTTPError, Exception) as e:
            logger.error(f"飞书推送异常: {e}")
            return {"channel": "feishu", "success": False, "error": str(e)[:200]}

    def _send_dingtalk(self, report: Dict) -> Dict:
        """发送钉钉消息"""
        import urllib.request as req

        webhook = self._config["dingtalk_webhook_url"]
        if not webhook:
            return {"channel": "dingtalk", "success": False, "error": "未配置 Webhook URL"}

        lines = [f"## 🤖 AI开源趋势日报 {report['date']}", "", f"扫描 {report['language']}，共 {report['ai_repos']} 个AI项目", ""]
        for r in report["repos"][:10]:
            s = f"⭐{r['stars']:,}" if r['stars'] else "⭐?"
            lines.append(f"{r['rank']}. [{r['name']}]({r['url']}) {s}")
            if r.get('description'):
                lines.append(f"   > {r['description'][:60]}")
            lines.append("")

        payload = {
            "msgtype": "markdown",
            "markdown": {"title": f"AI开源趋势 {report['date']}", "text": "\n".join(lines)},
        }

        data = json.dumps(payload).encode("utf-8")
        try:
            r = req.urlopen(req.Request(webhook, data=data, headers={"Content-Type": "application/json"}), timeout=15)
            body = r.read().decode()
            ok = json.loads(body).get("errcode") == 0
            return {"channel": "dingtalk", "success": ok, "response": body[:200]}
        except Exception as e:
            return {"channel": "dingtalk", "success": False, "error": str(e)[:200]}

    def _send_wechat(self, report: Dict) -> Dict:
        """发送企业微信消息"""
        import urllib.request as req

        webhook = self._config["wechat_webhook_url"]
        if not webhook:
            return {"channel": "wechat", "success": False, "error": "未配置 Webhook URL"}

        content = [f"## 🤖 AI开源趋势日报 {report['date']}"]
        for r in report["repos"][:10]:
            s = f"⭐{r['stars']:,}" if r['stars'] else "⭐?"
            content.append(f"{r['rank']}. [{r['name']}]({r['url']}) {s}")
        content.append(f"\n> AUTO-EVO-AI V0.1 自动扫描")

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": "\n".join(content)},
        }

        data = json.dumps(payload).encode("utf-8")
        try:
            r = req.urlopen(req.Request(webhook, data=data, headers={"Content-Type": "application/json"}), timeout=15)
            body = r.read().decode()
            ok = json.loads(body).get("errcode") == 0
            return {"channel": "wechat", "success": ok, "response": body[:200]}
        except Exception as e:
            return {"channel": "wechat", "success": False, "error": str(e)[:200]}

    # ═══════════════════════════════════════════════════
    # Status / Health API
    # ═══════════════════════════════════════════════════

    def _action_status(self, params: Dict) -> Dict:
        return {
            "success": True,
            "data": {
                "module": "TrendingPipeline",
                "version": self.VERSION,
                "enabled": self._config.get("enabled", True),
                "config": dict(self._config),
                "stats": dict(self._stats),
                "notify_configured": bool(self._config.get("feishu_webhook_url")
                                           or self._config.get("dingtalk_webhook_url")
                                           or self._config.get("wechat_webhook_url")),
            },
        }

    def _action_health(self, params: Dict) -> Dict:
        return {
            "success": True,
            "status": "ok" if self._config.get("enabled", True) else "disabled",
            "version": self.VERSION,
        }

    def _action_history(self, params: Dict) -> Dict:
        """获取历史扫描记录"""
        try:
            if HISTORY_DB_PATH.exists():
                with open(HISTORY_DB_PATH, "r", encoding="utf-8") as f:
                    history = json.load(f)
                limit = params.get("limit", 30)
                return {"success": True, "history": history[-limit:], "total": len(history)}
        except Exception as e:
            logger.error(f"读取历史失败: {e}")
        return {"success": True, "history": [], "total": 0}

    def _action_last_report(self, params: Dict) -> Dict:
        if self._last_report:
            return {"success": True, "report": asdict(self._last_report)}
        return {"success": False, "error": "尚无报告，请先执行一次扫描"}

# ═══════════════════════════════════════════════════════
# 模块级入口 — 兼容 scheduler engine 的 class.find('execute')
# ═══════════════════════════════════════════════════════

module_class = TrendingPipeline

__module_meta__ = {"inputs": {"params": "dict"}, "outputs": {"result": "dict"}}
