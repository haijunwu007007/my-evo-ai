"""
任意GitHub仓库自动转化为系统MCP工具/Skill
使用场景: "把这个开源项目接入本系统"
流程: 扫描仓库 → 分析API/CLI → 生成MCP配置 → 注册为Skill
"""
import os, json, logging, subprocess, tempfile, shutil, urllib.request, re

logger = logging.getLogger("gitmcp_converter")

class GitMCPConverter:
    def __init__(self):
        self._converted = {}

    def get_status(self):
        return {"success": True, "converted": len(self._converted), "repos": list(self._converted.keys())}

    def convert(self, repo_url: str) -> dict:
        """将GitHub仓库转化为系统可用的MCP工具"""
        # 提取owner/name
        m = re.search(r'github\.com[:/]([\w-]+/[\w-]+?)(?:\.git)?$', repo_url)
        if not m:
            m = re.search(r'^([\w-]+/[\w-]+)$', repo_url)
        if not m:
            return {"success": False, "error": "无法解析仓库路径"}
        repo = m.group(1)
        name = repo.split("/")[-1]

        # 尝试GitMCP
        try:
            r = urllib.request.urlopen(f"https://gitmcp.io/{repo}", timeout=15)
            tools = json.loads(r.read())
            self._converted[repo] = {"name": name, "mode": "gitmcp", "tools": tools if isinstance(tools, list) else [tools]}
            return {"success": True, "repo": repo, "mode": "gitmcp", "tools": self._converted[repo]["tools"]}
        except: pass

        # 降级: 扫描README/SKILL.md
        try:
            r = urllib.request.urlopen(f"https://api.github.com/repos/{repo}/contents", timeout=10)
            files = json.loads(r.read())
            readme = [f for f in files if f["name"].lower() in ("readme.md", "skill.md", "README.md")]
            self._converted[repo] = {"name": name, "mode": "readme", "files": [f["name"] for f in readme]}
            return {"success": True, "repo": repo, "mode": "readme", "note": "已识别仓库，建议手动完善SKILL.md"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def list(self) -> list:
        return [{"repo": k, **v} for k, v in self._converted.items()]

module_class = GitMCPConverter
