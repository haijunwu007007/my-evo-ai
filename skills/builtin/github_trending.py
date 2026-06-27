"""GitHub Trending 技能 — 爬取热门项目"""
import urllib.request, re, json

skill_def = {
    "name": "github-trending", "version": "1.0.0",
    "description": "GitHub 今日热门项目 TOP 10",
    "author": "AUTO-EVO-AI", "category": "搜索", "icon": "🔥",
    "tags": ["GitHub", "热门", "趋势", "开源"],
    "input_schema": {"type": "object", "properties": {"language": {"type": "string"}, "limit": {"type": "integer"}}},
    "output_schema": {"type": "object", "properties": {"projects": {"type": "array"}}}
}

def execute(params, context=None):
    lang = params.get("language", "")
    limit = int(params.get("limit", 10))
    url = "https://github.com/trending"
    if lang: url += f"/{lang}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        projects = []
        articles = re.findall(r'<article[^>]*class="Box-row"[^>]*>(.*?)</article>', html, re.DOTALL)
        for art in articles[:limit]:
            m = re.search(r'href="/([^/"]+)/([^/"]+)"', art)
            if not m: continue
            owner, repo = m.group(1), m.group(2)
            desc_m = re.search(r'<p[^>]*class="col-9"[^>]*>(.*?)</p>', art, re.DOTALL)
            desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip() if desc_m else ""
            stars_m = re.findall(r'octicon-star[^>]*></svg>\s*([^<\s]+)', art)
            stars = stars_m[0].strip() if stars_m else "?"
            projects.append({
                "name": f"{owner}/{repo}",
                "url": f"https://github.com/{owner}/{repo}",
                "description": desc[:200],
                "stars": stars
            })
        return {"projects": projects}
    except Exception as e:
        return {"projects": [], "error": f"获取失败：{e}"}
