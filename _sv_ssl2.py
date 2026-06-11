import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='Hj711201', timeout=15, look_for_keys=False, allow_agent=False)
print('SSH_OK')

def run(cmd, t=30):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(0.5)
    out = b''
    while o.channel.recv_ready(): out += o.channel.recv(4096)
    return out.decode(errors='replace').strip()[-600:]

# Current nginx config
print('=== nginx server_name ===')
print(run('grep server_name /etc/nginx/sites-enabled/evo.conf', 5))

# Run certbot
print('=== Certbot ===')
print(run('sudo certbot --nginx -d autoevoai.com --non-interactive --agree-tos --email admin@autoevoai.com 2>&1', 90))

# Nginx test
print('=== nginx -t ===')
print(run('sudo nginx -t 2>&1', 5))

# Verify HTTPS with real cert
time.sleep(2)
import httpx
try:
    r = httpx.get('https://122.51.144.227/', verify=False, timeout=10)
    print(f'HTTPS(IP): {r.status_code}')
except:
    pass
try:
    r = httpx.get('https://autoevoai.com/', verify=False, timeout=10)
    print(f'HTTPS(domain): {r.status_code} {len(r.text)}b')
except Exception as e:
    print(f'HTTPS(domain) err: {type(e).__name__}')

ssh.close()
print('DONE')
