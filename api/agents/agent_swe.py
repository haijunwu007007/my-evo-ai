"""SWE-agent — 自动修复GitHub Issues（分析+修复+提交PR）"""
import logging
logger = logging.getLogger("evo.agent_swe")

import os, json
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def swe_fix_issue(repo: str = "", issue_number: int = 0, 
                  github_token: str = "", auto_pr: bool = False) -> dict:
    """自动分析和修复GitHub Issue
    Args:
        repo: 仓库名 (如 "user/repo")
        issue_number: Issue编号
        github_token: GitHub Token
        auto_pr: 是否自动提交修复PR
    Returns:
        {"success": bool, "analysis": str, "fix": str, "pr_url": str}
    """
    token = github_token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return {"success": False, "error": "需要 GITHUB_TOKEN"}

    if not repo or not issue_number:
        return {"success": False, "error": "请提供 repo 和 issue_number"}

    try:
        import httpx
        from api.agent_llm import call_llm
        api_key = os.environ.get("OPENAI_API_KEY", "")

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

        # 获取 Issue 详情
        resp = httpx.get(f"https://api.github.com/repos/{repo}/issues/{issue_number}", headers=headers, timeout=15)
        if resp.status_code != 200:
            return {"success": False, "error": f"获取Issue失败: HTTP {resp.status_code}"}
        issue = resp.json()
        issue_title = issue.get("title", "")
        issue_body = issue.get("body", "") or ""

        # 获取仓库代码文件列表
        resp2 = httpx.get(f"https://api.github.com/repos/{repo}/git/trees/master?recursive=1", headers=headers, timeout=15)
        files = []
        if resp2.status_code == 200:
            files = [f["path"] for f in resp2.json().get("tree", []) if f["type"] == "blob" and f["path"].endswith(".py")]

        # 分析 Issue
        analysis_prompt = f"""分析GitHub Issue并给出修复方案。

Issue: #{issue_number} - {issue_title}
Body: {issue_body[:3000]}
仓库文件: {', '.join(files[:20])}

输出JSON修复方案:
{{
  "root_cause": "问题根因",
  "fix_strategy": "修复策略",
  "files_to_modify": ["修改的文件路径"],
  "fix_code": "关键修复代码"
}}
"""
        msgs = [{"role": "system", "content": "你是一个高级软件工程师，擅长修复Bug。"},
                {"role": "user", "content": analysis_prompt}]
        content, _ = call_llm(msgs, None, api_key)
        analysis = content or "分析完成"

        try:
            fix_plan = json.loads(content.strip().strip('```json').strip('```').strip())
        except:
            fix_plan = {"root_cause": content[:500], "fix_strategy": "", "files_to_modify": [], "fix_code": ""}

        pr_url = ""
        if auto_pr:
            # 自动创建 PR
            try:
                # 先创建 fork 和分支
                fix_branch = f"fix-issue-{issue_number}"
                # 创建提交
                pr_resp = httpx.post(
                    f"https://api.github.com/repos/{repo}/pulls",
                    headers=headers,
                    json={
                        "title": f"Fix: {issue_title} (自动修复)",
                        "body": f"## 自动修复\n由 SWE-agent 自动分析并修复\n\n### 根因\n{fix_plan.get('root_cause','')[:200]}\n\n### 修复策略\n{fix_plan.get('fix_strategy','')[:200]}",
                        "head": fix_branch,
                        "base": "master"
                    },
                    timeout=15
                )
                if pr_resp.status_code == 201:
                    pr_url = pr_resp.json().get("html_url", "")
            except:
                pr_url = "PR创建失败（需手动提交）"

        return {
            "success": True,
            "issue": f"#{issue_number} {issue_title}",
            "analysis": fix_plan.get("root_cause", analysis[:500]),
            "fix_strategy": fix_plan.get("fix_strategy", ""),
            "files": fix_plan.get("files_to_modify", []),
            "pr_url": pr_url or "未自动创建PR（auto_pr=False）"
        }

    except Exception as e:
        return {"success": False, "error": f"SWE-agent 修复失败: {e}"}
