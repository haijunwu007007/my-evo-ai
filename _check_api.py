import urllib.request, json

# Try quicktools endpoint
for ep in ['/api/v1/quicktools','/api/quicktools','/api/v1/tools','/api/tools']:
    try:
        r = urllib.request.urlopen('https://autoevoai.com'+ep, timeout=5)
        d = json.loads(r.read())
        print(f'{ep}: status={r.status} success={d.get("success",False)} count={len(d.get("tools",[]) or d.get("quicktools",[]) or [])}')
    except Exception as e:
        print(f'{ep}: {type(e).__name__}')
