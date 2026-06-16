import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# Read the file
_,o,_=C.exec_command("cat -n /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10,get_pty=True)
lines=o.read().decode().split('\n')
# Find lines to keep (first occurrence of each import pattern)
kept=set()
good_lines=[]
for ln in lines:
    l=ln.strip()
    if l.startswith('from __future__'): good_lines.append(l); continue
    if l.startswith('"""') and not good_lines: good_lines.append(l); continue
    if l.startswith('import os') or l.startswith('from pathlib') or l.startswith('from api.hub') or l.startswith('from core.logging'):
        k=l.split('#')[0].strip()
        if k not in kept:
            kept.add(k); good_lines.append(l)
    else:
        good_lines.append(l)
# write back
sftp=C.open_sftp()
with sftp.open('/tmp/clean.py','w') as f:
    f.write('\n'.join(good_lines)+'\n')
sftp.close()
C.exec_command("sudo cp /tmp/clean.py /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10)
_,o,_=C.exec_command("head -10 /home/ubuntu/my-evo-ai/api/hub/integrate.py",timeout=10,get_pty=True)
print(o.read().decode()[:400])
C.close()
