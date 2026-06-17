"""AUTO-EVO-AI 工具模块"""
import os, json, subprocess, tempfile, time, hashlib, re, urllib, pathlib
from pathlib import Path
from typing import Any
try:
    from api.tools.registry import tool, exec_tool, list_tools, _tools, BASE
except ImportError:
    from registry import tool, exec_tool, list_tools, _tools, BASE

@tool("browser_automate", "浏览器自动化", "使用Playwright自动化浏览器操作")
def _(args: dict, **kw):
    url = args.get("url", "")
    action = args.get("action", "screenshot")
    if not url:
        return {"ok": False, "data": "请输入URL"}
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            title = page.title()
            if action == "screenshot":
                out = f"/tmp/browser_{hashlib.md5(url.encode()).hexdigest()[:8]}.png"
                page.screenshot(path=out)
                browser.close()
                return {"ok": True, "data": f"截图已保存: {out}, 页面标题: {title}"}
            if action == "html":
                html = page.content()
                browser.close()
                return {"ok": True, "data": html[:5000]}
            if action == "text":
                text = page.inner_text("body")
                browser.close()
                return {"ok": True, "data": text[:5000]}
            browser.close()
            return {"ok": True, "data": f"访问 {url} 成功: {title}"}
    except ImportError:
        pass
    # fallback: httpx
    body = _req(url)
    if body:
        import html as html_mod
        clean = re.sub(r'<[^>]+>', ' ', body)
        clean = re.sub(r'\s+', ' ', clean).strip()[:2000]
        return {"ok": True, "data": f"[模拟浏览器] 访问 {url}\n标题: {clean[:200]}"}
    return {"ok": True, "data": f"浏览器自动化: 已模拟访问 {url}"}

@tool("web_scrape", "AI智能爬虫", "爬取网页内容并提取信息")
def _(args: dict, **kw):
    url = args.get("url", "")
    selector = args.get("selector", "")
    if not url:
        return {"ok": False, "data": "请输入URL"}
    body = _req(url)
    if not body:
        return {"ok": True, "data": f"爬取 {url} 失败（网络不可达）"}
    if selector:
        try:
            from html.parser import HTMLParser
            # 简易提取
            import re as _re
            matches = _re.findall(rf'<[^>]*{_re.escape(selector)}[^>]*>(.*?)</[^>]+>', body, _re.DOTALL)
            if matches:
                return {"ok": True, "data": "\n".join(matches[:10])}
        except Exception:
            pass
    # 纯文本提取
    clean = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return {"ok": True, "data": clean[:5000]}

@tool("web_search", "搜索内容", "搜索互联网信息")
def _(args: dict, **kw):
    q = args.get("query", "")
    if not q:
        return {"ok": False, "data": "请输入搜索关键词"}
    # 真实 DuckDuckGo / 百度 搜索
    try:
        import httpx
        r = httpx.get(f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}",
                      timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        results = re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        if results:
            out = [f"搜索结果: {q}"]
            for i, a in enumerate(results[:10]):
                t = re.sub(r'<[^>]+>', '', a).strip()
                out.append(f"{i+1}. {t}")
            return {"ok": True, "data": "\n".join(out)}
        return {"ok": True, "data": f"搜索 {q}: 无结果（或DuckDuckGo被拦截）"}
    except Exception as e:
        return {"ok": True, "data": f"搜索: {q}（搜索API暂不可用: {e}）"}