"""Fix: asyncio.run nested loop issue in agent_llm.py"""
import re

with open('/home/ubuntu/my-evo-ai/api/agent_llm.py', 'r') as f:
    content = f.read()

# The problematic async _race function needs to be replaced with sync version
old_code = """        async def _race():
            async def _try_async(p):
                return p, await asyncio.to_thread(_try_provider, p, messages, tools, t, key)
            done, _ = await asyncio.wait([_try_async(p) for p in top2],
                                          return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                p, r = task.result()
                if r:
                    _mark_ok(p["name"])
                    return r
                _mark_fail(p["name"])
            # \u90fd\u5931\u8d25\u5219\u4e32\u884c\u8bd5\u5269\u4f59
            for p in free_providers[2:]:
                if _in_cooldown(p): continue
                r = _try_provider(p, messages, tools, t, key)
                if r:
                    _mark_ok(p["name"])
                    return r
                _mark_fail(p["name"])
            return None
        result = asyncio.run(_race())"""

new_code = """        # \u540c\u6b65\u5e76\u884c\uff1a\u76f4\u63a5\u8c03\u7528\u800c\u4e0d\u7528asyncio.run (\u907f\u514d\u5d4c\u5957\u4e8b\u4ef6\u5faa\u73af)
        for p in top2:
            try:
                r = _try_provider(p, messages, tools, t, key)
                if r:
                    _mark_ok(p["name"])
                    return r
            except Exception:
                _mark_fail(p["name"])
        for p in free_providers[2:]:
            if _in_cooldown(p): continue
            try:
                r = _try_provider(p, messages, tools, t, key)
                if r:
                    _mark_ok(p["name"])
                    return r
            except Exception:
                _mark_fail(p["name"])"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/home/ubuntu/my-evo-ai/api/agent_llm.py', 'w') as f:
        f.write(content)
    print("FIXED: replaced async _race with sync version")
else:
    print("WARN: old_code not found, checking if already fixed...")
    if 'asyncio.run(_race())' in content:
        print("asyncio.run still present - different code structure")
        print("Lines around asyncio.run:")
        for i, line in enumerate(content.split('\n')):
            if 'asyncio.run' in line:
                print(f"  L{i+1}: {line.strip()[:100]}")
                # Print surrounding lines
                surrounding = content.split('\n')[max(0,i-15):i+3]
                for j, sl in enumerate(surrounding):
                    print(f"  L{max(0,i-15)+j+1}: {sl[:100]}")
                break
    else:
        print("Seems already fixed!")
