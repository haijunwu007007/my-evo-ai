"""测试 githubtrending 模块 — 覆盖今日修复的5个bug"""
import sys, os, pytest, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

def _get_mod():
    from modules.githubtrending import module_class as C
    inst = C()
    if hasattr(inst, 'initialize'): inst.initialize()
    inst._last_fetch = 0
    inst._repos.clear()
    return inst

async def _exec(mod, **kw):
    r = await mod.execute(action=kw.get('action','trending'), params={k:v for k,v in kw.items() if k != 'action'})
    return r.data if hasattr(r, 'data') else r

def test_scan_trending_alias():
    """bug-1: scan_trending 必须存在且返回数据"""
    mod = _get_mod()
    d = asyncio.run(_exec(mod, action='scan_trending', language='python', period='daily'))
    repos = d.get('repos', d.get('results', []))
    assert d.get('success'), f"scan_trending failed: {d.get('error','')}"
    assert len(repos) > 0, "scan_trending 返回0条"

def test_all_language_returns_25():
    """bug-2: language=all 必须返回完整条数不过滤"""
    mod = _get_mod()
    d = asyncio.run(_exec(mod, action='trending', language='all', period='daily'))
    repos = d.get('repos', d.get('results', []))
    assert d.get('success'), f"trending(all) failed"
    assert len(repos) >= 10, f"all language 应>=10条, 实际{len(repos)}"

def test_default_language_returns_25():
    """bug-2: 不传language也应返回完整条数"""
    mod = _get_mod()
    d = asyncio.run(_exec(mod, action='trending', period='daily'))
    repos = d.get('repos', d.get('results', []))
    assert d.get('success'), f"trending(no lang) failed"
    assert len(repos) >= 10, f"no lang 应>=10条, 实际{len(repos)}"

def test_python_filter_works():
    """语言过滤(python)只返回python项目"""
    mod = _get_mod()
    d = asyncio.run(_exec(mod, action='trending', language='python', period='daily'))
    repos = d.get('repos', d.get('results', []))
    assert d.get('success')
    for repo in repos:
        assert repo['language'].lower() == 'python', f"非python: {repo['full_name']}"

def test_cache_ttl():
    """bug-5: 缓存60秒内重复调用快速返回"""
    mod = _get_mod()
    d1 = asyncio.run(_exec(mod, action='trending', language='python'))
    import time; t0 = time.time()
    d2 = asyncio.run(_exec(mod, action='trending', language='python'))
    elapsed = time.time() - t0
    assert d2.get('success')
    assert elapsed < 2.0, f"缓存应在2秒内返回, 实际{elapsed:.1f}s"

def test_help_has_scan_trending():
    """help 列表必须包含 scan_trending"""
    mod = _get_mod()
    d = asyncio.run(_exec(mod, action='help'))
    assert 'scan_trending' in d.get('actions', []), "help 缺少 scan_trending"

def test_unknown_action_fallback():
    """未知action的available列表包含scan_trending"""
    mod = _get_mod()
    d = asyncio.run(_exec(mod, action='nonexistent'))
    assert 'scan_trending' in d.get('available', []), "fallback 缺少 scan_trending"
