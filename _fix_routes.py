"""修复真正的路由冲突 — routes_services.py + core.py 去重"""
import pathlib, re

root = pathlib.Path('D:/AUTO-EVO-AI-V0.1')

# 1. routes_services.py — 删除与专用路由文件重复的端点
svc = root / 'api' / 'routes' / 'routes_services.py'
c = svc.read_text('utf-8', errors='ignore')
o = c

# 这些端点由专用路由文件实现，routes_services.py的版本是重复的
# 添加注释说明
fragments = [
    ('GET /api/v1/rag/documents', 'rag 文档列表，由 routes_rag.py 实现'),
    ('POST /api/v1/rag/upload', 'rag 上传，由 routes_rag.py 实现'),
    ('GET /api/v1/llm/providers', 'LLM提供商列表，由 routes_llm_chat.py 实现'),
    ('POST /api/v1/llm/chat', 'LLM聊天，由 routes_llm_chat.py 实现'),
    ('GET /api/v1/plugins', '插件列表，由 routes_plugins.py 实现'),
]

# 找对应函数并注释掉
for path_str, note in fragments:
    # 找对应的 @router.get/post(...) 和 def ...
    pattern = re.compile(
        rf'(@router\.\w+\(["\']{re.escape(path_str)}["\'].*?\))\n'
        r'(async )?def \w+\(', 
        re.DOTALL
    )
    m = pattern.search(c)
    if m:
        start = m.start()
        # 找到函数体结束 (下一个 def 或 @router)
        rest = c[start:]
        end = re.search(r'\n(@router\.|\n\n\n)', rest)
        if end:
            func_end = start + end.start()
        else:
            func_end = len(c)
        func_text = c[start:func_end]
        comment = f'# [DUPLICATE] {path_str} — {note}\n# 已禁用，由专用路由文件实现\n# '
        c = c[:start] + comment + func_text.replace('\n', '\n# ') + '\n'
        print(f'  已禁用: {path_str} by {note}')
    else:
        print(f'  未找到: {path_str}')

if c != o:
    svc.write_text(c, 'utf-8')
    print('routes_services.py 已更新')

# 2. core.py — 删除与专用路由文件重复的端点
core = root / 'api' / 'routes' / 'features' / 'core.py'
if core.exists():
    c = core.read_text('utf-8', errors='ignore')
    o = c
    core_frags = [
        ('POST /api/v1/email/send', '邮件发送，由 routes_email.py 实现'),
        ('POST /api/v1/rerank', '重排，由 routes_rerank.py 实现'),
    ]
    for path_str, note in core_frags:
        pattern = re.compile(
            rf'(@router\.\w+\(["\']{re.escape(path_str)}["\'].*?\))\n'
            r'(async )?def \w+\(', 
            re.DOTALL
        )
        m = pattern.search(c)
        if m:
            start = m.start()
            rest = c[start:]
            end = re.search(r'\n(@router\.|\n\n\n)', rest)
            if end:
                func_end = start + end.start()
            else:
                func_end = len(c)
            func_text = c[start:func_end]
            comment = f'# [DUPLICATE] {path_str} — {note}\n# 已禁用\n# '
            c = c[:start] + comment + func_text.replace('\n', '\n# ') + '\n'
            print(f'  已禁用: {path_str}')
    if c != o:
        core.write_text(c, 'utf-8')
        print('core.py 已更新')

print('\n语法检查...')
import py_compile
for f in [svc, core]:
    try:
        py_compile.compile(str(f), doraise=True)
        print(f'  OK {f.name}')
    except py_compile.PyCompileError as e:
        print(f'  ERR {f.name}: {e}')
