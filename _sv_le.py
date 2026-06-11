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
    return out.decode(errors='replace').strip()[-800:]

# Check DNS 
print('=== DNS ===')
print(run('host autoevoai.com 2>&1 || nslookup autoevoai.com 2>&1', 10))

# Current nginx config full
print('=== evo.conf ===')
print(run('cat /etc/nginx/sites-enabled/evo.conf', 5))

# Try certbot standalone mode (uses its own webserver on port 80 temporarily)
print('=== Certbot standalone ===')
print(run('sudo certbot certonly --standalone -d autoevoai.com --non-interactive --agree-tos --email admin@autoevoai.com --preferred-challenges http 2>&1', 90))

# If that worked, show cert paths
print('=== Certs ===')
print(run('ls -la /etc/letsencrypt/live/autoevoai.com/ 2>&1', 5))

# Update nginx to use real cert
print('=== Write nginx config ===')
print(run('''sudo tee /etc/nginx/sites-enabled/evo.conf << 'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl http2;
    server_name _;
    ssl_certificate /etc/letsencrypt/live/autoevoai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/autoevoai.com/privkey.pem;
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

# Final verify
import httpx
try:
    r = httpx.get('https://autoevoai.com/', verify=False, timeout=10)
    print(f'HTTPS: {r.status_code}')
except Exception as e:
    print(f'HTTPS err: {type(e).__name__}: {str(e)[:60]}')

ssh.close()
print('DONE')
