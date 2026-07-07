"""Scan all frontend pages for sidebar infrastructure."""
import os

frontend = r'D:\AUTO-EVO-AI-V0.1\frontend'
files = sorted([f for f in os.listdir(frontend) if f.endswith('.html') and f != 'chat.html' and f != 'index.html'])

print(f"{'File':<25} {'Sbar':<6} {'Ham':<5} {'Ovl':<5} {'tglFn':<7} {'endlS':<7}")
print("-"*55)

has_sidebar = []
for fname in files:
    path = os.path.join(frontend, fname)
    text = open(path, 'r', encoding='utf-8', errors='ignore').read()
    sb = 'Y' if '.sidebar' in text else 'N'
    hm = 'Y' if 'hamburger' in text.lower() else 'N'
    ov = 'Y' if 'sidebar-overlay' in text or 'sidebarOverlay' in text else 'N'
    tf = 'Y' if 'toggleSidebar' in text else 'N'
    ls = 'Y' if '</html>' in text else 'N'
    print(f"{fname:<25} {sb:<6} {hm:<5} {ov:<5} {tf:<7} {ls:<7}")
    if 'sidebar' in text and '.sidebar' in text:
        has_sidebar.append(fname)

print(f"\nPages with sidebar: {len(has_sidebar)}")
for f in has_sidebar:
    print(f"  {f}")
