"""修复剩余问题: geo_search __future__ 位置 + /api/v1/version 端点"""
import re
from pathlib import Path

MODULES = Path("D:\\AUTO-EVO-AI-V0.1\\modules")
ROOT = Path("D:\\AUTO-EVO-AI-V0.1")

# 1. 修复 geo_search.py — __future__ 移到 docstring 之后
fp = MODULES / "geo_search.py"
content = fp.read_text(encoding='utf-8')

# 删除错误的 __future__ 行
content = content.replace("\nfrom __future__ import annotations\n", "\n", 1)

# 在 docstring 结束 (""") 后的第一个空行后插入
lines = content.split('\n')
insert_after = None
for i, line in enumerate(lines):
    if line.strip() == '"""' and i > 0:  # docstring 结束
        # 插入在下一行（空行）
        if i + 1 < len(lines) and lines[i + 1].strip() == '':
            insert_after = i + 1
        else:
            insert_after = i + 1
        break

if insert_after is not None:
    lines.insert(insert_after + 1, 'from __future__ import annotations')
    fp.write_text('\n'.join(lines), encoding='utf-8')
    print(f"✅ geo_search: __future__ 移到正确位置")
else:
    print(f"❌ geo_search: 未找到 docstring 结束位置")

# 2. 检查 agent_planner 的 ModuleRegistry 导入
fp = MODULES / "agent_planner.py"
content = fp.read_text(encoding='utf-8')
if 'from modules._base.registry import ModuleRegistry' in content:
    print(f"✅ agent_planner: ModuleRegistry 导入已存在")

# 3. 检查 registry.py 是否真有 ModuleRegistry
registry_fp = MODULES / "_base" / "registry.py"
if registry_fp.exists():
    registry_content = registry_fp.read_text(encoding='utf-8')
    if 'class ModuleRegistry' in registry_content:
        print(f"✅ _base/registry.py: 包含 ModuleRegistry 类")
    else:
        print(f"❌ _base/registry.py: 没有 ModuleRegistry 类！")
else:
    print(f"❌ _base/registry.py: 文件不存在")

# 4. 添加 /api/v1/version 端点 — 在 api_server.py 中
api_fp = ROOT / "api_server.py"
if api_fp.exists():
    content = api_fp.read_text(encoding='utf-8')
    # 查找现有的 /api/v1/status 端点，在其后添加 version 端点
    if "/api/v1/version" in content:
        print(f"✅ api_server.py: /api/v1/version 端点已存在")
    else:
        # 在 /api/v1/status 路由后插入
        pattern = r'(async def get_status.*?\n.*?return.*?\n)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            insert = '''\n\n@app.get("/api/v1/version")
async def get_version():
    """系统版本信息"""
    return {"success": True, "version": "V0.1", "build": "20260604", "modules": len(load_all_modules())}
'''
            # 找到 get_status 函数结束后插入
            end_pos = match.end()
            content = content[:end_pos] + insert + content[end_pos:]
            api_fp.write_text(content, encoding='utf-8')
            print(f"✅ api_server.py: 添加 /api/v1/version 端点")
        else:
            # 直接找 app.get("/api/v1/status")
            if '@app.get("/api/v1/status")' in content:
                pos = content.index('@app.get("/api/v1/status")')
                # 找该函数的 return 行
                rest = content[pos:]
                lines2 = rest.split('\n')
                ret_idx = None
                brace_count = 0
                for j, l in enumerate(lines2):
                    brace_count += l.count('{') - l.count('}')
                    if 'return' in l and brace_count >= 0:
                        ret_idx = j
                        break
                if ret_idx:
                    insert_after_line = pos + len('\n'.join(lines2[:ret_idx+1]))
                    version_ep = '''
@app.get("/api/v1/version")
async def get_version():
    """系统版本信息"""
    return {"success": True, "version": "V0.1", "build": "20260604"}
'''
                    content = content[:insert_after_line] + version_ep + '\n' + content[insert_after_line:]
                    api_fp.write_text(content, encoding='utf-8')
                    print(f"✅ api_server.py: 添加 /api/v1/version (方式2)")
            else:
                print(f"❌ api_server.py: 未找到 /api/v1/status 路由")
else:
    print(f"❌ api_server.py: 文件不存在")

print("\n修复完成!")
