#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
# 直接加个debug端点
C.exec_command('''sudo tee -a /home/ubuntu/my-evo-ai/api/routes/routes_hub.py << 'DEBUG'
@router.get("/hub-debug")
async def hub_debug():
    from api.hub.discover import _fallback_popular
    try:
        p = _fallback_popular()
        return {"len": len(p), "first": p[0]["name"] if p else "none", "cat": p[0].get("category","?")}
    except Exception as e:
        return {"error": str(e)}
DEBUG
''', timeout=10)
C.exec_command("sudo systemctl restart evo.service", timeout=10)
import time;time.sleep(5)
_,o,_=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/hub-debug 2>/dev/null", timeout=10, get_pty=True)
print("Debug:", o.read().decode()[:300])
C.close()
