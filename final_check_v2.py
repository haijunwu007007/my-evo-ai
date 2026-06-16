import paramiko, time
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
time.sleep(3)
paths=['/api/v1/hub/discover','/api/v1/hub/projects','/api/v1/hub/composes','/api/v1/hub/templates','/api/v1/company/status']
for p in paths:
    _,r,_=C.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" -m 5 http://127.0.0.1:8765{p}',timeout=10,get_pty=True)
    c=r.read().decode().strip()
    print(f'[{"OK" if c=="200" else "NO"}] {p}: {c}')
# 测试docker可用
_,d,_=C.exec_command('docker info --format "{{.ServerVersion}}" 2>/dev/null||echo no_docker',timeout=10,get_pty=True)
print(f'Docker: {d.read().decode().strip()[:30]}')
# 测试git可用
_,g,_=C.exec_command('git --version 2>/dev/null',timeout=10,get_pty=True)
print(f'Git: {g.read().decode().strip()[:30]}')
# 测试pip install portainer
_,p,_=C.exec_command('pip3 list 2>/dev/null|grep -i docker',timeout=10,get_pty=True)
print(f'DockerPy: {p.read().decode().strip()[:30]}')
C.close()
