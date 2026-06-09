"""Install and configure CloudFlare Tunnel"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, t=30):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(2)
    r = b''
    while o.channel.recv_ready(): r += o.channel.recv(4096)
    return r.decode(errors='replace').strip()[:800]

# Step 1: Install cloudflared
print('1:', run('curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared && chmod +x /tmp/cloudflared && sudo mv /tmp/cloudflared /usr/local/bin/ && cloudflared version', 60))

# Step 2: Create systemd service for quick tunnel
service = """[Unit]
Description=Cloudflare Tunnel for AUTO-EVO-AI
After=network.target

[Service]
Type=simple
User=ubuntu
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:8766
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
import base64
b64 = base64.b64encode(service.encode()).decode()
print('2:', run(f'echo {b64} | base64 -d | sudo tee /etc/systemd/system/cloudflared.service && sudo systemctl daemon-reload && sudo systemctl enable cloudflared', 10))

# Step 3: Start tunnel
print('3:', run('sudo systemctl start cloudflared', 10))
time.sleep(8)

# Step 4: Check logs for the URL
print('4:', run('sudo journalctl -u cloudflared --no-pager -n 30 2>&1', 10))

# Step 5: Update nginx to keep serving HTTP on 80
print('5:', run('curl -sk http://127.0.0.1:8765/api/v1/version', 10))

ssh.close()
print('DONE')
