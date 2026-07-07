"""Check which sidebar pages are missing share.css."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

DIR = r'D:\AUTO-EVO-AI-V0.1\frontend'
pages = ['enterprise.html','agents.html','skills.html','capabilities.html',
         'billion-os.html','experts.html','claw.html','human.html','hermes.html',
         'admin.html','automations.html','loop.html','learn.html','hub.html',
         'cognee.html','deploy.html','video.html','agent.html','settings.html',
         'apps.html','review.html','dashboard.html','canvas.html']

print(f"{'页面':<24} {'share.css':<12} {'viewport':<12}")
print('-'*48)

for fn in pages:
    path = os.path.join(DIR, fn)
    if not os.path.exists(path):
        print(f"{fn:<24} {'N/A':<12} {'N/A':<12}")
        continue
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        c = f.read()
    has_sc = 'share.css' in c
    has_vp = 'name="viewport"' in c
    sc_s = 'OK' if has_sc else 'MISS'
    vp_s = 'OK' if has_vp else 'MISS'
    print(f"{fn:<24} {sc_s:<12} {vp_s:<12}")
