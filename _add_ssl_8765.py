import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

# Create a new nginx config that listens on 8765 with SSL
new_config = """
server {
    server_name 122.51.144.227 autoevoai.com www.autoevoai.com;
    listen 8765 ssl;
    ssl_certificate /etc/letsencrypt/live/autoevoai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/autoevoai.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:18765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:18765;
        proxy_read_timeout 120s;
    }
}
"""

sftp = s.open_sftp()
with sftp.open("/etc/nginx/sites-available/evo_ssl_8765", "w") as f:
    f.write(new_config)
sftp.close()

s.exec_command("ln -sf /etc/nginx/sites-available/evo_ssl_8765 /etc/nginx/sites-enabled/ 2>/dev/null")
i,o,e = s.exec_command("sudo nginx -t 2>&1")
t = (o.read()+e.read()).decode()
print("nginx test:", t[:200])

if "test is successful" in t:
    s.exec_command("sudo nginx -s reload")
    print("reloaded")
    
    # Also update the evo service to listen on a different port so nginx can proxy
    i2,o2,e2 = s.exec_command("sudo grep -o '127.0.0.1:8765' /etc/nginx/sites-available/autoevoai.com | head -1")
    print("Current proxy:", o2.read().decode()[:50])
    
    # Move evo service to 18765, nginx proxies 8765->18765 with SSL
    s.exec_command("sudo sed -i 's|bind.*0.0.0.0:8765|bind 0.0.0.0:18765|' /etc/evo.env 2>/dev/null")
    s.exec_command("sudo systemctl restart evo.service")
    print("evo restarted")
else:
    print("nginx test failed")

s.close()
