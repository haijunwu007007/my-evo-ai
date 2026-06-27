"""给深色页面注入浅色主题CSS变量"""
import os

FRONTEND = r'D:\AUTO-EVO-AI-V0.1\frontend'

pages = [
    'dashboard.html', 'hub.html', 'automations.html', 'company.html',
    'canvas.html', 'workflow.html', 'capabilities.html', 'deploy.html',
    'video.html', 'agents.html',
]

# 浅色主题变量
LIGHT_THEME = """
/* 浅色主题覆盖 */
:root{--bg:#f5f5f8;--bg2:#f0f0f4;--card:#fff;--text:#1a1a2e;--text2:#6b7280;--border:#e8eaed;--accent:#4361ee;--shadow:0 1px 3px rgba(0,0,0,.08);--hover:rgba(67,97,238,.06)}
body{background:#f5f5f8!important;color:#1a1a2e!important}
"""

for fname in pages:
    path = os.path.join(FRONTEND, fname)
    if not os.path.exists(path):
        print(f"SKIP {fname}")
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 注入浅色主题（在第一个</style>之前或<head>尾部）
    inject = '<style>' + LIGHT_THEME + '</style>\n'
    
    if '<style>' in content:
        # 插入到第一个<style>之后
        pos = content.index('<style>') + 7
        content = content[:pos] + '\n' + LIGHT_THEME + '\n' + content[pos:]
    elif '</head>' in content:
        pos = content.index('</head>')
        content = content[:pos] + inject + content[pos:]
    else:
        print(f"SKIP {fname} 无style/head")
        continue
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {fname}")

print("全部完成")
