"""重新部署v6 — 获取422详细错误"""
import urllib.request, json

HOST = "https://autoevoai.com"

# 获取详细错误
try:
    data = json.dumps({"cmd":"echo test","timeout":10}).encode()
    r = urllib.request.urlopen(f"{HOST}/api/v1/cli/exec", data, timeout=10)
    print(f"200: {r.read().decode()[:200]}")
except Exception as e:
    print(f"Error: {str(e)[:500]}")
    
# 获取openapi/schema
try:
    r = urllib.request.urlopen(f"{HOST}/openapi.json", timeout=10)
    schema = json.loads(r.read())
    # 找ExecRequest
    if 'components' in schema and 'schemas' in schema['components']:
        for name, s in schema['components']['schemas'].items():
            if 'exec' in name.lower() or 'cli' in name.lower():
                print(f"\n{name}: {json.dumps(s, ensure_ascii=False)[:200]}")
except Exception as e:
    print(f"Schema error: {e}")
