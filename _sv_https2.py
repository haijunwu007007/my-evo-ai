"""Step by step HTTPS setup"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, timeout=15):
    _,o,_ = ssh.exec_command(cmd, timeout=timeout)
    import time as t; t.sleep(0.5)
    return o.read(errors='replace').decode(errors='replace').strip()[:500]

# Step 1: Generate self-signed cert
print('S1:', run('sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/nginx/selfsigned.key -out /etc/nginx/selfsigned.crt -subj "/CN=autoevoai.com" -addext "subjectAltName=DNS:autoevoai.com,IP:122.51.144.227" 2>&1', 20))

# Step 2: Check old nginx config
print('S2:', run('ls -la /etc/nginx/sites-enabled/', 5))
print('S2b:', run('cat /etc/nginx/sites-enabled/default 2>/dev/null | head -3 || echo NO_FILE', 5))

# Step 3: Write new config
import base64
new_cfg = base64.b64encode("""
server {
    listen 80;
    server_name autoevoai.com 122.51.144.227;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl http2;
    server_name autoevoai.com 122.51.144.227;
    ssl_certificate /etc/nginx/selfsigned.crt;
    ssl_certificate_key /etc/nginx/selfsigned.key;
    client_max_body_size 100M;
    location / {
        proxy_pass http://127.0.0.1:8766;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
""".encode()).decode()

cmd = f'echo {base64.b64encode(new_cfg.encode()).decode()} | base64 -d | sudo tee /etc/nginx/sites-enabled/default > /dev/null'
print('S3:', run(f'echo {new_cfg} | base64 --decode | sudo tee /etc/nginx/sites-enabled/default > /dev/null && echo OK', 10))

# Step 4: Reload
print('S4:', run('sudo nginx -t 2>&1', 10))
print('S4b:', run('sudo systemctl reload nginx 2>&1', 10))

# Step 5: Test from server
print('S5:', run('curl -sk https://127.0.0.1/api/v1/version 2>&1 | head -3', 10))

# Step 6: Port status
print('S6:', run('ss -tlnp | grep -E "80|443"', 5))
print('S6b:', run('sudo ufw status 2>/dev/null || echo UFW_N/A', 5))

ssh.close()
print('DONE')
