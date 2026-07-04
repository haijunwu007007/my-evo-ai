import sys, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
resp = urllib.request.urlopen('https://autoevoai.com/', timeout=10)
html = resp.read().decode('utf-8')
checks = [
    ('输入框 width:100%', 'width:100%' in html),
    ('输入框 flex:1 1 auto', 'flex:1 1 auto' in html),
    ('toggleRightPanel 修复', "btn.style.right=''" in html),
    ('箭头方向展开▶', 'right-panel-visible .right-toggle-btn::after{content:"▶"}' in html),
    ('按钮位置CSS控制', 'right:-8px' in html),
]
for name, ok in checks:
    print(f'  {"✅" if ok else "❌"} {name}')
print(f'文件大小: {len(html)} bytes')
