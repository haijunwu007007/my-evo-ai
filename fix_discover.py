#!/usr/bin/env python3
import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=15)
# 快速测试 Python 代码
_,o,_=C.exec_command('python3 -c "
from api.hub.discover import _fallback_popular
p = _fallback_popular()
print(f\"len={len(p)}\")
print(f\"first={p[0][\"name\"]}\")
print(f\"cat={p[0].get(\\\"category\\\")}\")
" 2>&1',timeout=10,get_pty=True)
print(o.read().decode()[:300])
C.close()
