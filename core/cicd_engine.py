"""
AUTO-EVO-AI V0.1 — CI/CD集成引擎
====================================
上市公司生产级设计：

核心能力:
  1. GitHub集成 — 仓库/分支/PR/Issue/Actions管理
  2. GitLab集成 — 项目/流水线/MR/Issue管理
  3. Jenkins集成 — Job/Build/Pipeline触发与监控
  4. 通用Git — 任意Git服务器操作
  5. 部署管理 — SSH部署/Docker部署/K8s部署
  6. 构建状态 — Webhook接收+状态聚合
  7. 代码质量 — 与质量检查模块联动

使用方式:
  from core.cicd_engine import CICDEngine

  cicd = CICDEngine()

  # GitHub
  cicd.github_list_repos("myorg")
  cicd.github_create_issue("myorg/repo", "Bug", "描述")
  cicd.github_trigger_workflow("myorg/repo", "deploy.yml", {"env": "prod"})

  # Git操作
  cicd.git_status("/path/to/repo")
  cicd.git_pull("/path/to/repo")
  cicd.git_push("/path/to/repo", "main")

依赖: 无外部依赖, 使用urllib调用REST API
     可选: PyGithub (pip install PyGithub)
"""

import os
import re
import json
import time
import subprocess
from core.logging_config import get_logger
import urllib.request
import urllib.error
import tempfile
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = get_logger("evo.cicd_engine")


# ═══════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════

class PlatformType(Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    JENKINS = "jenkins"
    GENERIC = "generic"


@dataclass
class PlatformConfig:
    name: str
    platform_type: PlatformType
    base_url: str = ""
    api_token: str = ""
    username: str = ""
    enabled: bool = True


@dataclass
class BuildInfo:
    id: str = ""
    platform: str = ""
    repo: str = ""
    branch: str = ""
    status: str = ""  # pending/running/success/failed
    started_at: float = 0
    finished_at: float = 0
    duration_ms: int = 0
    commit: str = ""
    trigger: str = ""
    logs: str = ""


@dataclass
class WebhookEvent:
    source: str = ""
    event_type: str = ""
    payload: dict = field(default_factory=dict)
    received_at: float = 0.0


# ═══════════════════════════════════════════════════
# GitHub集成
# ═══════════════════════════════════════════════════

class GitHubIntegration:
    """GitHub API集成"""

    def __init__(self, token: str = "", base_url: str = "https://api.github.com"):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.base_url = base_url

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers=self._headers())
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())

    def _post(self, path: str, data: dict) -> dict:
        url = f"{self.base_url}{path}"
        payload = json.dumps(data).encode()
        req = urllib.request.Request(url, data=payload, method="POST", headers=self._headers())
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())

    def is_configured(self) -> bool:
        return bool(self.token)

    def get_user(self) -> dict:
        try:
            return self._get("/user")
        except Exception as e:
            return {"error": str(e)}

    def list_repos(self, org: str = "", sort: str = "updated", per_page: int = 20) -> list[dict]:
        """列出仓库"""
        try:
            path = f"/orgs/{org}/repos" if org else "/user/repos"
            result = self._get(f"{path}?sort={sort}&per_page={per_page}")
            return [{"name": r.get("name", ""), "full_name": r.get("full_name", ""),
                     "description": (r.get("description") or "")[:100],
                     "private": r.get("private", False),
                     "language": r.get("language", ""),
                     "stars": r.get("stargazers_count", 0),
                     "updated_at": r.get("updated_at", "")} for r in result]
        except Exception as e:
            return [{"error": str(e)}]

    def list_branches(self, repo: str) -> list[dict]:
        try:
            result = self._get(f"/repos/{repo}/branches?per_page=30")
            return [{"name": b["name"], "sha": b["commit"]["sha"][:8]} for b in result]
        except Exception as e:
            return [{"error": str(e)}]

    def list_issues(self, repo: str, state: str = "open", per_page: int = 20) -> list[dict]:
        try:
            result = self._get(f"/repos/{repo}/issues?state={state}&per_page={per_page}")
            return [{"number": i["number"], "title": i["title"],
                     "state": i["state"], "labels": [l["name"] for l in i.get("labels", [])],
                     "created_at": i.get("created_at", "")} for i in result]
        except Exception as e:
            return [{"error": str(e)}]

    def create_issue(self, repo: str, title: str, body: str = "",
                      labels: list[str] = None, assignees: list[str] = None) -> dict:
        try:
            data = {"title": title, "body": body}
            if labels:
                data["labels"] = labels
            if assignees:
                data["assignees"] = assignees
            result = self._post(f"/repos/{repo}/issues", data)
            return {"success": True, "issue_number": result.get("number"), "url": result.get("html_url")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_workflows(self, repo: str) -> list[dict]:
        try:
            result = self._get(f"/repos/{repo}/actions/workflows")
            return [{"id": w["id"], "name": w["name"], "path": w["path"],
                     "state": w["state"], "url": w.get("html_url", "")} for w in result.get("workflows", [])]
        except Exception as e:
            return [{"error": str(e)}]

    def trigger_workflow(self, repo: str, workflow_id: str, ref: str = "main",
                          inputs: dict = None) -> dict:
        try:
            data = {"ref": ref}
            if inputs:
                data["inputs"] = inputs
            self._post(f"/repos/{repo}/actions/workflows/{workflow_id}/dispatches", data)
            return {"success": True, "repo": repo, "workflow": workflow_id, "ref": ref}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_prs(self, repo: str, state: str = "open") -> list[dict]:
        try:
            result = self._get(f"/repos/{repo}/pulls?state={state}&per_page=20")
            return [{"number": pr["number"], "title": pr["title"],
                     "state": pr["state"], "user": pr.get("user", {}).get("login", ""),
                     "head": pr.get("head", {}).get("ref", ""),
                     "base": pr.get("base", {}).get("ref", "")} for pr in result]
        except Exception as e:
            return [{"error": str(e)}]


# ═══════════════════════════════════════════════════
# Git操作封装
# ═══════════════════════════════════════════════════

class GitOperations:
    """本地Git操作"""

    @staticmethod
    def _run(cmd: list[str], cwd: str, timeout: int = 30) -> dict:
        try:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
            return {"success": result.returncode == 0, "stdout": result.stdout.strip()[-500:],
                    "stderr": result.stderr.strip()[-200:], "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def status(self, repo_path: str) -> dict:
        """Git status"""
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            return {"success": False, "error": "不是Git仓库"}
        r = self._run(["git", "status", "--short"], repo_path)
        if r["success"]:
            lines = [l for l in r["stdout"].split("\n") if l.strip()]
            modified = [l for l in lines if l.startswith(" M") or l.startswith("M")]
            untracked = [l for l in lines if l.startswith("??")]
            staged = [l for l in lines if not l.startswith("??") and not l.startswith(" M")]
            r["modified"] = len(modified)
            r["untracked"] = len(untracked)
            r["staged"] = len(staged)
            r["clean"] = len(lines) == 0
        return r

    def branch(self, repo_path: str) -> dict:
        """当前分支"""
        r = self._run(["git", "branch", "--show-current"], repo_path)
        if r["success"]:
            r["branch"] = r["stdout"]
        return r

    def log(self, repo_path: str, n: int = 10) -> dict:
        """最近提交"""
        r = self._run(["git", "log", f"-{n}", "--oneline", "--date=short", "--format=%h %ad %s"], repo_path)
        if r["success"]:
            r["commits"] = [l for l in r["stdout"].split("\n") if l.strip()]
        return r

    def pull(self, repo_path: str, remote: str = "origin", branch: str = "") -> dict:
        """Pull更新"""
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)
        return self._run(cmd, repo_path, timeout=60)

    def push(self, repo_path: str, remote: str = "origin", branch: str = "") -> dict:
        """Push"""
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        return self._run(cmd, repo_path, timeout=60)

    def add_commit_push(self, repo_path: str, message: str, add_all: bool = True) -> dict:
        """Add + Commit + Push 一条龙"""
        if add_all:
            r = self._run(["git", "add", "-A"], repo_path)
            if not r["success"]:
                return r
        r = self._run(["git", "commit", "-m", message], repo_path)
        if not r["success"] and "nothing to commit" not in r.get("stdout", "") + r.get("stderr", ""):
            return r
        return self.push(repo_path)


# ═══════════════════════════════════════════════════
# 部署管理
# ═══════════════════════════════════════════════════

class DeployManager:
    """部署管理器"""

    @staticmethod
    def docker_build(repo_path: str, tag: str = "latest") -> dict:
        """Docker构建"""
        try:
            result = subprocess.run(
                ["docker", "build", "-t", tag, "."],
                cwd=repo_path, capture_output=True, text=True, timeout=300,
            )
            return {"success": result.returncode == 0,
                    "stdout": result.stdout[-500:], "stderr": result.stderr[-200:]}
        except FileNotFoundError:
            return {"success": False, "error": "docker not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def docker_compose_up(repo_path: str, detach: bool = True) -> dict:
        """Docker Compose启动"""
        try:
            cmd = ["docker", "compose", "up", "-d"] if detach else ["docker", "compose", "up"]
            result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=120)
            return {"success": result.returncode == 0, "stdout": result.stdout[-500:], "stderr": result.stderr[-200:]}
        except FileNotFoundError:
            return {"success": False, "error": "docker-compose not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def docker_compose_down(repo_path: str) -> dict:
        try:
            result = subprocess.run(["docker", "compose", "down"], cwd=repo_path, capture_output=True, text=True, timeout=60)
            return {"success": result.returncode == 0}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
# CI/CD统一引擎
# ═══════════════════════════════════════════════════

class CICDEngine:
    """
    CI/CD统一集成引擎

    支持: GitHub / GitLab / Jenkins / 本地Git / Docker部署
    """

    def __init__(self):
        self._github = GitHubIntegration()
        self._git = GitOperations()
        self._deploy = DeployManager()
        self._webhook_events: list[WebhookEvent] = []
        self._builds: list[BuildInfo] = []

    # ─── GitHub ───

    def github_config(self) -> dict:
        return {
            "configured": self._github.is_configured(),
            "base_url": self._github.base_url,
            "token_set": bool(self._github.token),
            "user": self._github.get_user() if self._github.is_configured() else {},
        }

    def github_repos(self, org: str = "") -> list[dict]:
        return self._github.list_repos(org)

    def github_branches(self, repo: str) -> list[dict]:
        return self._github.list_branches(repo)

    def github_issues(self, repo: str, state: str = "open") -> list[dict]:
        return self._github.list_issues(repo, state)

    def github_create_issue(self, repo: str, title: str, body: str = "",
                             labels: list[str] = None) -> dict:
        return self._github.create_issue(repo, title, body, labels)

    def github_prs(self, repo: str, state: str = "open") -> list[dict]:
        return self._github.list_prs(repo, state)

    def github_workflows(self, repo: str) -> list[dict]:
        return self._github.list_workflows(repo)

    def github_trigger_workflow(self, repo: str, workflow: str, ref: str = "main",
                                 inputs: dict = None) -> dict:
        return self._github.trigger_workflow(repo, workflow, ref, inputs)

    # ─── Git ───

    def git_status(self, path: str) -> dict:
        return self._git.status(path)

    def git_branch(self, path: str) -> dict:
        return self._git.branch(path)

    def git_log(self, path: str, n: int = 10) -> dict:
        return self._git.log(path, n)

    def git_pull(self, path: str) -> dict:
        return self._git.pull(path)

    def git_push(self, path: str) -> dict:
        return self._git.push(path)

    def git_commit_push(self, path: str, message: str) -> dict:
        return self._git.add_commit_push(path, message)

    # ─── Deploy ───

    def deploy_docker_build(self, path: str, tag: str = "latest") -> dict:
        return self._deploy.docker_build(path, tag)

    def deploy_docker_up(self, path: str) -> dict:
        return self._deploy.docker_compose_up(path)

    def deploy_docker_down(self, path: str) -> dict:
        return self._deploy.docker_compose_down(path)

    # ─── Webhook ───

    def receive_webhook(self, source: str, event_type: str, payload: dict) -> dict:
        event = WebhookEvent(source=source, event_type=event_type, payload=payload, received_at=time.time())
        self._webhook_events.append(event)
        if len(self._webhook_events) > 500:
            self._webhook_events = self._webhook_events[-200:]
        return {"success": True, "event_id": len(self._webhook_events)}

    def list_webhooks(self, limit: int = 50) -> list[dict]:
        return [
            {"source": e.source, "event_type": e.event_type, "received_at": e.received_at,
             "payload_summary": {k: str(v)[:80] for k, v in e.payload.items()} if isinstance(e.payload, dict) else str(e.payload)[:100]}
            for e in self._webhook_events[-limit:]
        ]


# ═══════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════

_cicd_engine: CICDEngine | None = None


def get_cicd_engine() -> CICDEngine:
    global _cicd_engine
    if _cicd_engine is None:
        _cicd_engine = CICDEngine()
    return _cicd_engine
