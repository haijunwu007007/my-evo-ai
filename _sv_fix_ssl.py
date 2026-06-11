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
    return out.decode(errors='replace').strip()[-500:]

# Check existing certs
print('=== Certs ===')
print(run('ls -la /etc/nginx/*.crt /etc/nginx/*.pem /etc/letsencrypt/* 2>&1', 5))

# Generate self-signed if missing
print('=== Generate cert ===')
print(run('sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/nginx/selfsigned.key -out /etc/nginx/selfsigned.crt -subj "/CN=122.51.144.227" 2>&1', 15))

# Fix nginx config with self-signed
print('=== Write config ===')
print(run('''sudo tee /etc/nginx/sites-enabled/evo.conf << 'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl http2;
    server_name _;
    ssl_certificate /etc/nginx/selfsigned.crt;
    ssl_certificate_key /etc/nginx/selfsigned.key;
    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
''', 10))

print(run('sudo nginx -t 2>&1', 5))
print(run('sudo systemctl reload nginx 2>&1', 5))

# Verify 
time.sleep(1)
import httpx
for url in ['https://122.51.144.227/', 'http://122.51.144.227/']:
    try:
        r = httpx.get(url, verify=False, timeout=10)
        print(f'{url}: {r.status_code} {len(r.text)}b')
    except Exception as e:
        print(f'{url}: {type(e).__name__}')

ssh.close()
print('DONE')
