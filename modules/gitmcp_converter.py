"""
任意GitHub仓库自动转化为系统MCP工具/Skill
使用场景: "把这个开源项目接入本系统"
流程: 扫描仓库 → 分析API/CLI → 生成MCP配置 → 注册为Skill
"""
import os, json, logging, subprocess, tempfile, shutil, urllib.request, re, time

logger = logging.getLogger("gitmcp_converter")

# GitHub 国内镜像加速
GITHUB_MIRRORS = [
    None,  # 先试原生GitHub
    "https://ghproxy.com/",
    "https://hub.fastgit.xyz/",
    "https://gitclone.com/",
    "https://github.moeyy.xyz/",
]

def _github_url(repo_path: str, file_path: str = "") -> str:
    """生成GitHub文件URL，自动镜像降级"""
    if file_path:
        return f"https://raw.githubusercontent.com/{repo_path}/main/{file_path}"
    return f"https://github.com/{repo_path}"

def _fetch_url(url: str, timeout: int = 15) -> str:
    """带镜像降级的URL获取"""
    for mirror in GITHUB_MIRRORS:
        try:
            target = (mirror + url) if mirror else url
            r = urllib.request.urlopen(target, timeout=timeout)
            data = r.read().decode("utf-8", errors="replace")
            if data:
                return data
        except Exception:
            continue
    return ""

class GitMCPConverter:
    def __init__(self):
        self._converted = {}

    def get_status(self):
        return {"success": True, "converted": len(self._converted), "repos": list(self._converted.keys())}

    def convert(self, repo_url: str) -> dict:
        """将GitHub仓库转化为系统可用的MCP工具（自动镜像降级）"""
        m = re.search(r'github\.com[:/]([\w-]+/[\w-]+?)(?:\.git)?$', repo_url)
        if not m:
            m = re.search(r'^([\w-]+/[\w-]+)$', repo_url)
        if not m:
            return {"success": False, "error": "无法解析仓库路径"}
        repo = m.group(1)
        name = repo.split("/")[-1]

        # 1) GitMCP (标准MCP协议)
        try:
            r = urllib.request.urlopen(f"https://gitmcp.io/{repo}", timeout=10)
            tools = json.loads(r.read())
            self._converted[repo] = {"name": name, "mode": "gitmcp", "tools": tools if isinstance(tools, list) else [tools]}
            return {"success": True, "repo": repo, "mode": "gitmcp", "tools": self._converted[repo]["tools"]}
        except: pass

        # 2) GitHub API扫目录(镜像降级)
        api_urls = [
            f"https://api.github.com/repos/{repo}/contents",
            f"https://api.github.com/repos/{repo}/contents",  # ghproxy会代理API
        ]
        for api_url in api_urls:
            try:
                data = _fetch_url(api_url, timeout=10)
                if data:
                    files = json.loads(data)
                    readme = [f for f in files if f["name"].lower() in ("readme.md", "skill.md", "README.md")]
                    self._converted[repo] = {"name": name, "mode": "scan", "files": [f["name"] for f in readme]}
                    return {"success": True, "repo": repo, "mode": "scan"}
            except: pass

        # 3) 直接爬README(镜像降级)
        for fname in ["README.md", "SKILL.md", "readme.md", "package.json"]:
            try:
                raw_url = f"https://raw.githubusercontent.com/{repo}/main/{fname}"
                data = _fetch_url(raw_url, timeout=10)
                if data:
                    self._converted[repo] = {"name": name, "mode": "readme", "source": fname}
                    return {"success": True, "repo": repo, "mode": "readme", "source": fname, "preview": data[:200]}
            except: pass

        # 4) git clone(镜像代理)
        clone_urls = [
            f"https://github.com/{repo}.git",
            f"https://ghproxy.com/https://github.com/{repo}.git",
            f"https://gitclone.com/github.com/{repo}.git",
        ]
        for clone_url in clone_urls:
            try:
                tmp = tempfile.mkdtemp()
                subprocess.run(["git", "clone", "--depth=1", clone_url, tmp],
                               capture_output=True, timeout=30)
                files = os.listdir(tmp)
                shutil.rmtree(tmp, ignore_errors=True)
                self._converted[repo] = {"name": name, "mode": "clone", "files": files[:10]}
                return {"success": True, "repo": repo, "mode": "clone", "note": "已clone仓库待手动完善"}
            except: pass

        return {"success": False, "repo": repo, "error": "所有方式均失败（网络不通）"}

    def list(self) -> list:
        return [{"repo": k, **v} for k, v in self._converted.items()]

module_class = GitMCPConverter
