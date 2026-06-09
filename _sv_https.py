"""Self-signed cert + nginx HTTPS on port 80"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

CHUNK = lambda c: ssh.exec_command(c, timeout=30)

# Step 1: Generate self-signed cert
print("=== Step 1: Generating self-signed cert ===")
cmd = """sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/nginx/selfsigned.key \
  -out /etc/nginx/selfsigned.crt \
  -subj "/CN=autoevoai.com" \
  -addext "subjectAltName=DNS:autoevoai.com,IP:122.51.144.227" 2>&1"""
_,o,_ = ssh.exec_command(cmd, timeout=15)
print(o.read().decode(errors='replace').strip()[:200])

# Step 2: Backup original nginx and write new config
print("\n=== Step 2: Writing nginx config ===")
new_conf = """
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
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8766;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
"""
# Write via heredoc to avoid escaping issues
cmd = f"""sudo tee /etc/nginx/sites-enabled/default << 'NGINX_EOF'
{new_conf}
NGINX_EOF"""
_,o,_ = ssh.exec_command(cmd, timeout=10)
print('Config written:', o.read().decode(errors='replace')[:100])

# Step 3: Test + reload
print("\n=== Step 3: Reload nginx ===")
_,o,_ = ssh.exec_command('sudo nginx -t 2>&1', timeout=10)
print('Test:', o.read().decode(errors='replace').strip()[:200])

_,o,_ = ssh.exec_command('sudo systemctl reload nginx 2>&1', timeout=10)
print('Reload:', o.read().decode(errors='replace').strip()[:200])

# Step 4: Test locally
print("\n=== Step 4: Local HTTPS test ===")
_,o,_ = ssh.exec_command('curl -sk https://127.0.0.1/api/v1/version 2>&1 | head -3', timeout=10)
print('HTTPS local test:', o.read().decode(errors='replace').strip()[:200])

# Step 5: Check port 443 from server
_,o,_ = ssh.exec_command('curl -sk https://122.51.144.227/api/v1/version 2>&1 | head -3', timeout=15)
print('HTTPS public test:', o.read().decode(errors='replace').strip()[:200])

_,o,_ = ssh.exec_command('ss -tlnp | grep 443', timeout=5)
print('Port 443 listener:', o.read().decode(errors='replace').strip()[:200])

ssh.close()
print('\nDONE')
