#!/usr/bin/env python3
import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
sftp=C.open_sftp()
# 同步更新后的hub.html（含按钮对接）
src=r'D:\AUTO-EVO-AI-V0.1'
sftp.put(f'{src}/frontend/hub.html', '/home/ubuntu/my-evo-ai/frontend/hub.html')
sftp.put(f'{src}/frontend/chat.html', '/home/ubuntu/my-evo-ai/frontend/chat.html')
sftp.close()
C.exec_command('sudo systemctl restart evo.service',timeout=10)
time.sleep(8)
# 最终全面验证
tests = {
    '聊天': '/',
    '开源中心': '/hub',
    '画布': '/canvas',
    '二次开发': '/fork',
    '新手引导': '/tutorial',
    '管理后台': '/admin',
    'API发现': '/api/v1/hub/discover',
    'API项目': '/api/v1/hub/projects',
    'API组合': '/api/v1/hub/composes',
    'API监控': '/api/v1/hub/monitor',
    'API搜索': '/api/v1/hub/search?q=ollama',
    'API Fork': '/api/v1/hub/forks',
}
print('=== 公网验证 ===')
for name, path in tests.items():
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:8765{path}',timeout=10,get_pty=True)
    code=r.read().decode().strip()
    mark = '✅' if code in ('200','301') else '❌'
    print(f'  {mark} {name}: {code}')
C.close()
