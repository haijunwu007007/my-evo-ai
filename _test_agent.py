import requests, sys, traceback
BASE = 'http://127.0.0.1:8765'
try:
    r = requests.post(BASE+'/api/v1/agent/run', json={'task': '搜索GitHub最新AI项目', 'context': ''}, timeout=60)
    d = r.json()
    sys.stdout.reconfigure(encoding='utf-8')
    print('Success:', d.get('success'))
    print('Status:', r.status_code)
    if d.get('success'):
        print('Steps:', len(d.get('steps', [])))
        print('Result:', str(d.get('result', ''))[:200])
    else:
        print('Error:', str(d.get('error', ''))[:200])
except Exception as e:
    print('Exception:', str(e)[:200])
    traceback.print_exc()
