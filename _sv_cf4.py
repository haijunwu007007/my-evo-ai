"""Re-download cloudflared fresh"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, t=30):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(1)
    r = b''
    while o.channel.recv_ready(): r += o.channel.recv(4096)
    while o.channel.recv_stderr_ready(): r += o.channel.recv_stderr(4096)
    return r.decode(errors='replace').strip()[:600]

# Remove old binary
print('RM:', run('sudo rm -f /usr/local/bin/cloudflared && sudo systemctl stop cloudflared 2>/dev/null', 5))

# Download fresh - use a specific version URL
print('DL:', run('wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /tmp/cloudflared && chmod +x /tmp/cloudflared && sudo mv /tmp/cloudflared /usr/local/bin/cloudflared && sleep 1 && /usr/local/bin/cloudflared version 2>&1', 120))

# If still fails, try via apt from cloudflare repo
print('REPO:', run('curl -sL https://pkg.cloudflare.com/cloudflared.gpg | sudo apt-key add - 2>&1; echo "deb https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list; sudo apt-get update -qq 2>&1 | tail -2; sudo apt-get install -y cloudflared -qq 2>&1 | tail -5; cloudflared version 2>&1', 180))

ssh.close()
