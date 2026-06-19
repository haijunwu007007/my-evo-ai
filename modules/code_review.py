"""
Grade: A
AUTO-EVO-AI V0.1 — AI Code Review Engine
基于 Git diff + LLM 的专业代码审查引擎
支持：审查未提交变更 / 审查 commit / 审查 PR / 分支对比
"""
from __future__ import annotations

__module_meta__ = {
    "id": "code-review",
    "name": "AI 代码审查引擎",
    "version": "V0.1",
    "group": "developer",
    "grade": "A",
    "description": "基于 Git diff + LLM 的专业代码审查引擎",
    "tags": ["code-review", "git", "ai", "quality"],
}

import subprocess, os, json, re, time, difflib
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

from modules._base import Result
from modules._base.enterprise_module import EnterpriseModule


@dataclass
class ReviewIssue:
    severity: str  # critical / major / minor / info
    category: str  # security / bug / style / performance / best_practice / documentation
    file: str
    line: int = 0
    message: str = ""
    suggestion: str = ""
    code_snippet: str = ""


@dataclass
class ReviewResult:
    review_id: str = ""
    timestamp: str = ""
    target_type: str = ""  # working_tree / commit / branch / pr
    target: str = ""
    issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    score: int = 100  # 0-100
    files_reviewed: list[str] = field(default_factory=list)
    total_lines: int = 0
    duration_ms: int = 0


_review_history: list[ReviewResult] = []
_REVIEW_DB_PATH = Path(__file__).parent.parent / ".evo_data" / "reviews.json"


def _load_history():
    global _review_history
    if _REVIEW_DB_PATH.exists():
        try:
            raw = json.loads(_REVIEW_DB_PATH.read_text(encoding="utf-8"))
            _review_history = [ReviewResult(**r) for r in raw[-50:]]
        except Exception:
            _review_history = []


def _save_history():
    _REVIEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = [asdict(r) for r in _review_history[-100:]]
    _REVIEW_DB_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_git(cmd: list[str], cwd: Optional[str] = None) -> tuple[str, str]:
    """执行 git 命令"""
    if not cwd:
        cwd = str(Path(__file__).parent.parent)
    try:
        r = subprocess.run(["git"] + cmd, capture_output=True, text=True, timeout=30, cwd=cwd)
        return r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    except FileNotFoundError:
        return "", "git not found"


def _parse_diff(diff_text: str) -> list[dict]:
    """解析 git diff 输出为结构化数据"""
    files = []
    current = None
    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            if current:
                files.append(current)
            m = re.search(r" b/(.+)$", line)
            current = {"file": m.group(1) if m else "unknown", "additions": 0, "deletions": 0, "chunks": [], "content": line + "\n"}
        elif current:
            current["content"] += line + "\n"
            if line.startswith("@@"):
                m = re.search(r"\+(\d+)", line)
                current["chunks"].append({"start_line": int(m.group(1)) if m else 0, "lines": []})
            elif line.startswith("+"):
                current["additions"] += 1
                if current["chunks"]:
                    current["chunks"][-1]["lines"].append(line)
            elif line.startswith("-"):
                current["deletions"] += 1
    if current:
        files.append(current)
    return files


class CodeReviewer:
    """AI 代码审查引擎"""

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path or str(Path(__file__).parent.parent)
        _load_history()

    def _call_llm(self, prompt: str, system: str = "你是资深代码审查专家，精通安全审计、性能优化和最佳实践。") -> str:
        """调用 LLM 进行审查"""
        try:
            from api.agent_llm import call_llm
            msgs = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt[:8000]},
            ]
            r, _ = call_llm(msgs, None, "")
            return r or "（LLM 审查未返回结果）"
        except Exception as e:
            return f"LLM 调用失败: {e}"

    def _parse_llm_review(self, text: str, file_path: str) -> list[ReviewIssue]:
        """解析 LLM 审查结果"""
        issues = []
        lines = text.split("\n")
        current_severity = "info"
        current_category = "best_practice"

        for line in lines:
            line_lower = line.lower()
            if "[critical]" in line_lower or "🔴" in line or "严重" in line:
                current_severity = "critical"
            elif "[major]" in line_lower or "🟠" in line or "主要" in line:
                current_severity = "major"
            elif "[minor]" in line_lower or "🟡" in line or "次要" in line:
                current_severity = "minor"
            elif "[info]" in line_lower or "🔵" in line or "建议" in line:
                current_severity = "info"

            if "安全" in line or "security" in line_lower:
                current_category = "security"
            elif "bug" in line_lower or "错误" in line:
                current_category = "bug"
            elif "性能" in line or "performance" in line_lower:
                current_category = "performance"
            elif "风格" in line or "style" in line_lower:
                current_category = "style"
            elif "文档" in line or "doc" in line_lower:
                current_category = "documentation"

            if line.strip().startswith("- ") or line.strip().startswith("* "):
                msg = line.strip().lstrip("-* ").strip()
                if msg:
                    line_num = 0
                    m = re.search(r":(\d+)", msg)
                    if m:
                        line_num = int(m.group(1))
                    issues.append(ReviewIssue(
                        severity=current_severity,
                        category=current_category,
                        file=file_path,
                        line=line_num,
                        message=msg[:200],
                    ))

        return issues

    def review_working_tree(self, staged: bool = False) -> ReviewResult:
        """审查工作区变更（未提交代码）"""
        start = time.time()
        cmd = ["diff", "--cached"] if staged else ["diff"]
        diff_text, err = _run_git(cmd, self.repo_path)
        files = _parse_diff(diff_text)

        result = ReviewResult(
            review_id=f"rev_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            target_type="working_tree",
            target="staged" if staged else "unstaged",
            files_reviewed=[f["file"] for f in files],
            total_lines=sum(f["additions"] + f["deletions"] for f in files),
        )
        result.duration_ms = int((time.time() - start) * 1000)

        if not files:
            result.summary = "✅ 没有未提交的变更"
            result.score = 100
            _review_history.append(result)
            _save_history()
            return result

        # LLM 审查每个文件
        all_issues = []
        for f in files:
            prompt = f"""请审查以下代码变更文件（{f['file']}），逐条列出问题：
变更统计：+{f['additions']} / -{f['deletions']}

变更内容：
```diff
{f['content'][:3000]}
```

请按以下格式逐条列出问题：
- [severity] [category] 描述信息

severity: critical/major/minor/info
category: security/bug/performance/style/best_practice
"""
            review_text = self._call_llm(prompt)
            issues = self._parse_llm_review(review_text, f["file"])
            all_issues.extend(issues)

        result.issues = all_issues

        # 评分
        critical_count = sum(1 for i in all_issues if i.severity == "critical")
        major_count = sum(1 for i in all_issues if i.severity == "major")
        result.score = max(0, 100 - critical_count * 15 - major_count * 5 - len(all_issues))

        # 摘要
        if all_issues:
            summary_prompt = f"""基于以下代码审查问题（{len(all_issues)}项），生成一段中文摘要（50字以内）：
{chr(10).join(f'- [{i.severity}] {i.category}: {i.message}' for i in all_issues[:10])}"""
            result.summary = self._call_llm(summary_prompt, "简洁总结") or f"发现 {len(all_issues)} 个问题"
        else:
            result.summary = "✅ 代码质量良好，未发现问题"

        _review_history.append(result)
        _save_history()
        return result

    def review_commit(self, commit_hash: str, compare_with: str = "") -> ReviewResult:
        """审查指定的 commit"""
        start = time.time()
        if compare_with:
            diff_text, _ = _run_git(["diff", f"{compare_with}..{commit_hash}"], self.repo_path)
        else:
            diff_text, _ = _run_git(["show", "--format=", commit_hash], self.repo_path)

        files = _parse_diff(diff_text)
        result = ReviewResult(
            review_id=f"rev_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            target_type="commit",
            target=f"{commit_hash[:12]} vs {compare_with}" if compare_with else commit_hash[:12],
            files_reviewed=[f["file"] for f in files],
            total_lines=sum(f["additions"] + f["deletions"] for f in files),
        )

        if not files:
            result.summary = "指定 commit 无代码变更"
            result.score = 100
            result.duration_ms = int((time.time() - start) * 1000)
            _review_history.append(result)
            _save_history()
            return result

        all_issues = []
        for f in files:
            prompt = f"""审查以下 commit 变更 ({f['file']}):
+{f['additions']} / -{f['deletions']}

```diff
{f['content'][:3000]}
```

按格式逐条列出问题，focus on security, bug, performance"""
            review_text = self._call_llm(prompt)
            all_issues.extend(self._parse_llm_review(review_text, f["file"]))

        result.issues = all_issues
        critical_count = sum(1 for i in all_issues if i.severity == "critical")
        major_count = sum(1 for i in all_issues if i.severity == "major")
        result.score = max(0, 100 - critical_count * 15 - major_count * 5)
        result.summary = f"发现 {len(all_issues)} 个问题 (critical:{critical_count} major:{major_count})" if all_issues else "✅ 代码质量良好"
        result.duration_ms = int((time.time() - start) * 1000)

        _review_history.append(result)
        _save_history()
        return result

    def review_branch(self, base_branch: str = "master", head_branch: str = "") -> ReviewResult:
        """审查分支对比"""
        if not head_branch:
            head_branch, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], self.repo_path)
            head_branch = head_branch.strip()

        diff_text, _ = _run_git(["diff", f"{base_branch}..{head_branch}"], self.repo_path)
        files = _parse_diff(diff_text)

        result = ReviewResult(
            review_id=f"rev_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            target_type="branch",
            target=f"{base_branch}..{head_branch}",
            files_reviewed=[f["file"] for f in files],
            total_lines=sum(f["additions"] + f["deletions"] for f in files),
        )
        result.duration_ms = 0

        if not files:
            result.summary = "两个分支无差异"
            result.score = 100
            _review_history.append(result)
            _save_history()
            return result

        all_issues = []
        for f in files[:10]:
            prompt = f"""审查分支变更 ({f['file']}):
```diff
{f['content'][:3000]}
```
列出问题"""
            review_text = self._call_llm(prompt)
            all_issues.extend(self._parse_llm_review(review_text, f["file"]))

        result.issues = all_issues
        result.score = max(0, 100 - sum(1 for i in all_issues if i.severity == "critical") * 15)
        result.summary = f"分支差异审查: {len(files)} 文件, {len(all_issues)} 问题" if all_issues else "✅ 分支差异无问题"
        result.duration_ms = int((time.time() - start) * 1000)

        _review_history.append(result)
        _save_history()
        return result

    def get_history(self, limit: int = 20) -> list[dict]:
        """获取审查历史"""
        return [asdict(r) for r in _review_history[-limit:]]

    def get_diff(self, target: str = "", compare: str = "") -> str:
        """获取原始 diff 文本"""
        if not target:
            stdout, _ = _run_git(["diff"], self.repo_path)
        elif compare:
            stdout, _ = _run_git(["diff", f"{compare}..{target}"], self.repo_path)
        else:
            stdout, _ = _run_git(["show", "--format=", target], self.repo_path)
        return stdout

    def get_commit_log(self, limit: int = 20) -> list[dict]:
        """获取 commit 日志"""
        stdout, _ = _run_git(
            ["log", f"--max-count={limit}", "--format=%H|%an|%s|%ai"],
            self.repo_path,
        )
        commits = []
        for line in stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 3)
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "message": parts[2],
                    "date": parts[3] if len(parts) > 3 else "",
                })
        return commits


class CodeReviewModule(EnterpriseModule):
    """企业级 AI 代码审查模块"""

    def __init__(self):
        super().__init__(module_id="code-review", name="AI 代码审查引擎")
        self.reviewer = CodeReviewer()

    async def initialize(self):
        self._status = "ready"
        return Result(success=True, message="Code Review 引擎就绪")

    async def execute(self, action: str, **params) -> Result:
        try:
            if action == "review":
                target = params.get("target", "working")
                if target == "commit":
                    r = self.reviewer.review_commit(params.get("hash", "HEAD"))
                elif target == "branch":
                    r = self.reviewer.review_branch(
                        params.get("base", "master"), params.get("head", "")
                    )
                else:
                    r = self.reviewer.review_working_tree(params.get("staged", False))
                return Result(success=True, data=asdict(r))

            elif action == "diff":
                text = self.reviewer.get_diff(params.get("target", ""), params.get("compare", ""))
                return Result(success=True, data={"diff": text})

            elif action == "history":
                return Result(success=True, data={"reviews": self.reviewer.get_history()})

            elif action == "commits":
                return Result(success=True, data={"commits": self.reviewer.get_commit_log()})

            elif action == "status":
                return Result(success=True, data={"status": self._status})

            return Result(success=False, error=f"未知动作: {action}")
        except Exception as e:
            return Result(success=False, error=str(e))

    async def health_check(self):
        return Result(success=True, data={"status": self._status})


# 单例
_code_reviewer = CodeReviewer()


def get_reviewer() -> CodeReviewer:
    return _code_reviewer
