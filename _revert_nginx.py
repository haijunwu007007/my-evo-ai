import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

# 1. Re-enable YDService
s.exec_command("sudo systemctl enable YDService 2>/dev/null; sudo systemctl start YDService 2>/dev/null; echo 'YD started'")

# 2. Restore original nginx config (before any changes today)
orig = """server {
    server_name autoevoai.com www.autoevoai.com 122.51.144.227;
    location / { proxy_pass http://127.0.0.1:8765; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-Proto $scheme; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; proxy_read_timeout 300s; }

    location /api/ { proxy_pass http://127.0.0.1:8765; proxy_read_timeout 120s; }

    listen 443 ssl; # managed by Certbot

    # n8n workflow - integreated
    location /n8n/ {
        proxy_pass http://127.0.0.1:5678/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }

    ssl_certificate /etc/letsencrypt/live/autoevoai.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/autoevoai.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    ssl_session_cache shared:SSL:10m;




}server {
    if ($host = www.autoevoai.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    if ($host = autoevoai.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80;
    server_name 122.51.144.227;
    return 301 https://$host$request_uri; # managed by Certbot




}
"""

sftp = s.open_sftp()
with sftp.open("/home/ubuntu/evo_nginx_revert.conf", "w") as f:
    f.write(orig)
sftp.close()

stdin, stdout, stderr = s.exec_command(
    "sudo cp /home/ubuntu/evo_nginx_revert.conf /etc/nginx/sites-available/autoevoai.com && sudo nginx -t 2>&1"
)
result = (stdout.read() + stderr.read()).decode()
print("test:", result[:200])

if "test is successful" in result:
    s.exec_command("sudo nginx -s reload")
    print("reloaded")
else:
    print("FAILED")

s.close()
