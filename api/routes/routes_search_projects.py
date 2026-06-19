"""
routes_search_projects.py — 多平台开源项目搜索引擎
支持: GitHub / HuggingFace / 国内镜像
"""
import httpx, json, asyncio
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/search", tags=["search"])

# ─── GitHub ───
_GITHUB_API = "https://api.github.com"
_HF_API = "https://huggingface.co/api"

async def _search_github(q: str, sort: str = "stars", page: int = 1, lang: str = ""):
    """搜索 GitHub 仓库"""
    qs = q
    if lang:
        qs += f"+language:{lang}"
    s = "stars" if sort == "stars" else "updated" if sort == "trending" else "best-match"
    url = f"{_GITHUB_API}/search/repositories?q={qs}&sort={s}&order=desc&per_page=20&page={page}"
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.get(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "EvoAI/1.0"})
            if r.status_code != 200:
                return {"source": "github", "error": f"HTTP {r.status_code}"}
            d = r.json()
            items = d.get("items", [])
            return {
                "source": "github",
                "total": min(d.get("total_count", 0), 1000),
                "results": [{
                    "id": it["id"],
                    "name": it["full_name"],
                    "url": it["html_url"],
                    "description": (it.get("description") or "")[:200],
                    "stars": it.get("stargazers_count", 0),
                    "forks": it.get("forks_count", 0),
                    "language": it.get("language") or "",
                    "updated": it.get("updated_at", ""),
                    "license": (it.get("license") or {}).get("spdx_id") if it.get("license") else "",
                } for it in items]
            }
    except Exception as e:
        return {"source": "github", "error": str(e)[:100]}

async def _search_huggingface(q: str, sort: str = "likes", page: int = 1):
    """搜索 HuggingFace 模型/数据集"""
    s = "likes" if sort == "stars" or sort == "trending" else "lastModified"
    url = f"{_HF_API}/models?search={q}&sort={s}&direction=-1&limit=20"
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.get(url, headers={"User-Agent": "EvoAI/1.0"})
            if r.status_code != 200:
                return {"source": "huggingface", "error": f"HTTP {r.status_code}"}
            items = r.json()
            return {
                "source": "huggingface",
                "total": len(items),
                "results": [{
                    "id": it.get("modelId", ""),
                    "name": it.get("modelId", ""),
                    "url": f"https://huggingface.co/{it.get('modelId', '')}",
                    "description": (it.get("description") or "")[:200],
                    "stars": it.get("likes", 0),
                    "forks": it.get("downloads", 0),
                    "language": it.get("pipeline_tag") or "",
                    "updated": it.get("lastModified", ""),
                    "license": it.get("config", {}).get("license", "") if isinstance(it.get("config"), dict) else "",
                } for it in items]
            }
    except Exception as e:
        return {"source": "huggingface", "error": str(e)[:100]}

async def _search_mirror(q: str, mirror_type: str, sort: str = "stars", page: int = 1):
    """搜索国内镜像源 (ghproxy / hf-mirror)"""
    if mirror_type == "github":
        return await _search_github(q, sort, page)  # Use same GitHub API
    elif mirror_type == "huggingface":
        return await _search_huggingface(q, sort, page)
    return {"source": mirror_type, "error": "unsupported"}

async def _search_hf_mirror(q: str, sort: str = "likes", page: int = 1):
    """搜索 HuggingFace 国内镜像 hf-mirror.com"""
    url = f"https://hf-mirror.com/api/models?search={q}&sort={sort}&direction=-1&limit=20"
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.get(url, headers={"User-Agent": "EvoAI/1.0"})
            if r.status_code != 200:
                return {"source": "hf-mirror", "error": f"HTTP {r.status_code}"}
            items = r.json()
            return {
                "source": "hf-mirror",
                "total": len(items),
                "results": [{
                    "id": it.get("modelId", ""),
                    "name": it.get("modelId", ""),
                    "url": f"https://hf-mirror.com/{it.get('modelId', '')}",
                    "clone_url": f"https://hf-mirror.com/{it.get('modelId', '')}",
                    "description": (it.get("description") or "")[:200],
                    "stars": it.get("likes", 0),
                    "forks": it.get("downloads", 0),
                    "language": it.get("pipeline_tag") or "",
                    "updated": it.get("lastModified", ""),
                    "license": it.get("config", {}).get("license", "") if isinstance(it.get("config"), dict) else "",
                } for it in items]
            }
    except Exception as e:
        return {"source": "hf-mirror", "error": str(e)[:100]}

def _make_ghproxy_url(orig_url: str) -> str:
    """将 GitHub URL 转为 ghproxy 镜像克隆地址"""
    if "github.com" in orig_url:
        return f"https://ghproxy.com/{orig_url}"
    return orig_url

# ─── Trending 热门 ───
async def _trending_github(lang: str = "", since: str = "weekly"):
    """获取 GitHub Trending"""
    url = f"https://github.com/trending/{lang}?since={since}"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as cl:
            r = await cl.get(url, headers={"User-Agent": "EvoAI/1.0"})
            if r.status_code != 200:
                return {"source": "trending", "error": f"HTTP {r.status_code}"}
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            articles = soup.select("article.Box-row")
            results = []
            for art in articles[:30]:
                h = art.select_one("h2 a")
                if not h:
                    continue
                name = h.get("href", "").strip("/")
                desc_el = art.select_one("p")
                desc = desc_el.text.strip() if desc_el else ""
                stars_el = art.select_one(".d-inline-block.float-sm-right")
                stars = 0
                if stars_el:
                    try:
                        stars = int(stars_el.text.strip().replace(",", ""))
                    except:
                        stars = 0
                lang_el = art.select_one("[itemprop='programmingLanguage']")
                lang = lang_el.text.strip() if lang_el else ""
                results.append({
                    "name": name,
                    "url": f"https://github.com/{name}",
                    "description": desc[:200],
                    "stars": stars,
                    "language": lang,
                })
            return {"source": "trending", "total": len(results), "results": results}
    except ImportError:
        # no bs4, return error
        return {"source": "trending", "error": "需要安装 beautifulsoup4", "results": []}
    except Exception as e:
        return {"source": "trending", "error": str(e)[:100], "results": []}

# ─── 分类列表 ───
_GITHUB_CATEGORIES = [
    ("ai-ml", "AI/机器学习"), ("web-framework", "Web框架"), ("dev-tools", "开发工具"),
    ("frontend", "前端"), ("backend", "后端"), ("database", "数据库"),
    ("python", "Python"), ("javascript", "JavaScript"), ("go", "Go"),
    ("rust", "Rust"), ("blockchain", "区块链"), ("mobile", "移动开发"),
    ("devops", "DevOps"), ("game", "游戏"), ("security", "安全"),
]
_HF_CATEGORIES = [
    ("text-generation", "文本生成"), ("image-generation", "图像生成"),
    ("text-to-image", "文生图"), ("text-to-speech", "语音"),
    ("image-classification", "图像分类"), ("object-detection", "目标检测"),
    ("automatic-speech-recognition", "语音识别"), ("translation", "翻译"),
    ("summarization", "摘要"), ("question-answering", "问答"),
    ("video", "视频"), ("multimodal", "多模态"),
]

# ─── API 端点 ───

@router.get("/projects")
async def search_projects(
    q: str = Query("", description="关键词"),
    source: str = Query("github", description="来源: github/huggingface/all/github-mirror/hf-mirror"),
    sort: str = Query("stars", description="排序: stars/trending/relevance"),
    page: int = Query(1, ge=1),
    lang: str = Query("", description="编程语言筛选"),
    category: str = Query("", description="分类筛选"),
):
    """多平台搜索开源项目"""
    keyword = q or category
    tasks = []
    if source in ("github", "all", "github-mirror"):
        tasks.append(_search_github(keyword, sort, page, lang))
    if source in ("huggingface", "all", "hf-mirror"):
        tasks.append(_search_huggingface(keyword, sort, page))
    if source == "hf-mirror":
        tasks.append(_search_hf_mirror(keyword, sort, page))
    if source == "github-mirror":
        tasks.append(_search_github(keyword, sort, page, lang))  # same API, different label

    if not tasks:
        tasks.append(_search_github(keyword, sort, page, lang))

    results = await asyncio.gather(*tasks)

    # Add ghproxy clone URLs for github results
    for src in results:
        if src.get("source") in ("github", "github-mirror", "trending"):
            for r in src.get("results", []):
                if "clone_url" not in r:
                    r["clone_url"] = _make_ghproxy_url(r.get("url", r.get("name", "")))
                r["mirror_note"] = "国内镜像: ghproxy.com"

    merged = {
        "success": True,
        "query": q,
        "source": source,
        "sort": sort,
        "page": page,
        "sources": results,
    }
    return merged

@router.get("/trending")
async def trending_projects(
    lang: str = Query("", description="编程语言"),
    since: str = Query("weekly", description="weekly/daily/monthly"),
    source: str = Query("github", description="github/huggingface"),
):
    """获取热门项目"""
    if source == "huggingface":
        return await _search_huggingface("", "likes", 1)
    return await _trending_github(lang, since)

@router.get("/categories")
async def list_categories(source: str = Query("github", description="github/huggingface")):
    """获取分类列表"""
    if source == "huggingface":
        return {"success": True, "categories": [{"id": k, "name": v} for k, v in _HF_CATEGORIES]}
    return {"success": True, "categories": [{"id": k, "name": v} for k, v in _GITHUB_CATEGORIES]}
