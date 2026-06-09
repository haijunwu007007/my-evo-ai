"""Step by step HTTPS setup"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, timeout=15):
    _,o,_ = ssh.exec_command(cmd, timeout=timeout)
    time.sleep(1)
    raw = b''
    while o.channel.recv_ready():
        raw += o.channel.recv(4096)
    return raw.decode(errors='replace').strip()[:500]

# Step 1: Generate self-signed cert
print('S1:', run('sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /etc/nginx/selfsigned.key -out /etc/nginx/selfsigned.crt -subj "/CN=autoevoai.com" -addext "subjectAltName=DNS:autoevoai.com,IP:122.51.144.227" 2>&1', 25))

# Step 2: Check old config
print('S2:', run('ls -la /etc/nginx/sites-enabled/ 2>&1', 5))

# Step 3: Write nginx config
new_cfg = """server {
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
"""
import base64
b64 = base64.b64encode(new_cfg.encode()).decode()
cmd = f'echo {b64} | base64 -d | sudo tee /etc/nginx/sites-enabled/default > /dev/null && echo OK'
print('S3:', run(cmd, 10))

# Step 4: Test + reload
print('S4:', run('sudo nginx -t 2>&1', 10))

# Step 5: Check cert files
print('S5:', run('ls -la /etc/nginx/selfsigned.*', 5))
print('S5b:', run('sudo systemctl reload nginx 2>&1', 10))

# Step 6: Test HTTPS locally
print('S6:', run('curl -sk https://127.0.0.1/api/v1/version 2>&1 | head -3', 10))

# Step 7: Port status
print('S7:', run('ss -tlnp | grep -E "80|443"', 5))

# Step 8: Try from public IP (from server itself)
print('S8:', run('curl -sk --connect-timeout 5 https://122.51.144.227/api/v1/version 2>&1 | head -3', 15))

# Step 9: Also keep HTTP working on port 80 (redirect)
http_cfg = 'server { listen 80; server_name autoevoai.com 122.51.144.227; return 301 https://$host$request_uri; }'
b64http = base64.b64encode(http_cfg.encode()).decode()
cmd2 = f'echo {b64http} | base64 -d | sudo tee /etc/nginx/sites-enabled/http_redirect > /dev/null && echo OK'
print('S9:', run(cmd2, 5))
print('S9b:', run('sudo nginx -t 2>&1', 5))
print('S9c:', run('sudo systemctl reload nginx 2>&1', 5))

ssh.close()
print('DONE')
