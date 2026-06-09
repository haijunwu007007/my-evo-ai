"""PR-Agent (Qodo) — AI代码审查自动化"""
import os, json
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def review_pull_request(pr_url: str = "", repo: str = "", pr_number: int = 0, 
                        github_token: str = "", auto_fix: bool = False) -> dict:
    """AI自动审查Pull Request
    Args:
        pr_url: PR完整URL（如 https://github.com/user/repo/pull/123）
        repo: 仓库名（如 "user/repo"，和pr_number配合）
        pr_number: PR编号
        github_token: GitHub Token（默认从环境变量读取）
        auto_fix: 是否自动提交修复建议
    Returns:
        {"success": bool, "summary": str, "issues": list, "suggestions": list}
    """
    try:
        from pr_agent import PRAgent
    except ImportError:
        # 尝试从 qodo 导入
        try:
            from qodo import pr_agent
            PRAgent = pr_agent
        except ImportError:
            return {"success": False, "error": "pr-agent 未安装。运行: pip install pr-agent"}

    token = github_token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return {"success": False, "error": "需要 GITHUB_TOKEN 环境变量"}

    if not pr_url and not (repo and pr_number):
        return {"success": False, "error": "请提供 pr_url 或 repo+pr_number"}

    try:
        # PR-Agent API 调用
        # 简化版：直接调用 GitHub API + LLM 审查
        import httpx

        if not pr_url and repo and pr_number:
            pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"

        # 获取 PR 的 diff
        diff_url = pr_url.replace("https://api.github.com/", "https://api.github.com/") if "api.github.com" in pr_url else f"{pr_url}"
        if "api.github.com" not in diff_url:
            diff_url = f"https://api.github.com/repos/{pr_url.split('github.com/')[1].split('/pull/')[0]}/pulls/{pr_url.split('/pull/')[1]}"

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3.diff"}
        resp = httpx.get(diff_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            # 直接使用 PR 号码获取
            parts = pr_url.rstrip("/").split("/")
            pr_num = parts[-1]
            repo_full = "/".join(parts[-4:-2])
            diff_url = f"https://api.github.com/repos/{repo_full}/pulls/{pr_num}"
            resp = httpx.get(diff_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"}, timeout=30)

        diff = resp.text if resp.status_code == 200 else ""

        if not diff:
            return {"success": False, "error": f"无法获取PR diff: HTTP {resp.status_code}"}

        # 用 LLM 审查 diff
        from api.agent_llm import call_llm
        api_key = os.environ.get("OPENAI_API_KEY", "")
        review_prompt = f"""你是一个严格的代码审查专家。审查以下代码变更(diff)，输出JSON格式:

{{
  "summary": "总体审查结论",
  "issues": [{{"severity":"high/medium/low","file":"文件名","line":行号,"description":"问题描述","suggestion":"修复建议"}}],
  "suggestions": ["全局改进建议1", "全局改进建议2"]
}}

Diff:
{diff[:8000]}
"""

        messages = [{"role": "system", "content": "你是一个严格的代码审查专家。输出纯JSON。"},
                    {"role": "user", "content": review_prompt}]
        content, _ = call_llm(messages, None, api_key)
        
        if content:
            try:
                review = json.loads(content.strip().strip('```json').strip('```').strip())
            except:
                review = {"summary": content[:500], "issues": [], "suggestions": []}
        else:
            review = {"summary": "审查完成", "issues": [], "suggestions": []}

        return {
            "success": True,
            "summary": review.get("summary", ""),
            "issues": review.get("issues", []),
            "suggestions": review.get("suggestions", []),
            "pr_url": pr_url,
            "diff_size": len(diff)
        }

    except Exception as e:
        return {"success": False, "error": f"代码审查失败: {e}"}
