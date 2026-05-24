"""测试 coordinator — 覆盖截断bug"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

def test_trending_25_results():
    from modules.githubtrending import module_class as C
    inst = C()
    if hasattr(inst, 'initialize'): inst.initialize()
    inst._last_fetch = 0; inst._repos.clear()
    r = asyncio.run(inst.execute(action='trending', params={'language':'all','period':'daily'}))
    d = r.data if hasattr(r, 'data') else r
    repos = d.get('repos', d.get('results', []))
    assert d.get('success'), f"trending failed: {d.get('error','')}"
    assert len(repos) == 25, f"应返回25条, 实际{len(repos)}"
