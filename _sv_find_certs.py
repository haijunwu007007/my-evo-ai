"""Find SSL certs and nginx config"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Full search for SSL certs
cmds = [
    'find / -name "fullchain.pem" 2>/dev/null | head -5',
    'find / -name "privkey.pem" 2>/dev/null | head -5',
    'find / -name "*.crt" -not -path "*/proc/*" 2>/dev/null | head -5',
    'find / -name "*.key" -not -path "*/proc/*" -not -path "*/sys/*" 2>/dev/null | head -5',
    'cat /etc/nginx/nginx.conf 2>/dev/null',
    'cat /etc/nginx/conf.d/default.conf 2>/dev/null',
    'cat /etc/nginx/sites-enabled/default 2>/dev/null',
    'cat /etc/nginx/conf.d/evo.conf 2>/dev/null',
    'ls /etc/nginx/conf.d/ 2>/dev/null',
    'ls /etc/nginx/sites-enabled/ 2>/dev/null',
]
for c in cmds:
    _,o,_ = ssh.exec_command(c, timeout=8)
    r = o.read().decode(errors='replace').strip()
    if r:
        print(f'=== {c[:60]} ===')
        print(r[:500])
        print()

ssh.close()
