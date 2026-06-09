"""Find SSL and nginx config - faster searches"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

cmds = [
    'find /etc/nginx -name "*.conf" 2>/dev/null; find /etc/nginx -name "*.pem" 2>/dev/null; find /etc/ssl -name "*.pem" 2>/dev/null; echo "---"; find /etc/letsencrypt -name "fullchain.pem" 2>/dev/null; echo "---"; ls -la /etc/nginx/conf.d/ 2>/dev/null; echo "---"; ls -la /etc/nginx/sites-enabled/ 2>/dev/null; echo "---"; cat /etc/nginx/nginx.conf 2>/dev/null | head -60; echo "---"; cat /etc/nginx/conf.d/evo.conf 2>/dev/null; echo "---"; cat /etc/nginx/sites-enabled/default 2>/dev/null | head -60',
]
for c in cmds:
    _,o,_ = ssh.exec_command(c, timeout=10)
    r = o.read().decode(errors='replace').strip()
    print(r[:2000])

ssh.close()
