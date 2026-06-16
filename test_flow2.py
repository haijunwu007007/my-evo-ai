import sys, paramiko, time
sys.stdout.reconfigure(encoding='utf-8')
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# Skip add, integrate already attempted
# Check status
r=C.exec_command("curl -s -m 5 http://127.0.0.1:8765/api/v1/hub/projects/portainer/status 2>/dev/null",timeout=10,get_pty=True)
raw=r[1].read().decode(errors='replace')
print("Status:",raw[:600])
# docker ps
r2=C.exec_command("docker ps --format '{{.Names}}\t{{.Status}}'|grep -i portainer",timeout=10,get_pty=True)
print("Docker:",r2[1].read().decode(errors='replace')[:200])
C.close()
