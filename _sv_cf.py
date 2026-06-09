"""Install cloudflared and set up tunnel"""
import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

# Check if cloudflared already exists
_,o,_ = ssh.exec_command('which cloudflared 2>/dev/null || echo NOT_FOUND', timeout=5)
r = o.read().decode().strip()
print(f'cloudflared: {r}')

if r == 'NOT_FOUND':
    # Download with wget (more reliable from China)
    print('Downloading cloudflared...')
    _,o,_ = ssh.exec_command(
        'wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 '
        '-O /tmp/cloudflared 2>&1 && chmod +x /tmp/cloudflared && sudo mv /tmp/cloudflared /usr/local/bin/cloudflared && echo OK',
        timeout=120
    )
    r = o.read().decode(errors='replace').strip()
    print(f'Download: {r[:200]}')

# Verify
_,o,_ = ssh.exec_command('cloudflared --version 2>&1', timeout=10)
print('Version:', o.read().decode(errors='replace').strip()[:100])

# Quick tunnel test
print('\nStarting quick tunnel...')
_,o,_ = ssh.exec_command(
    'nohup cloudflared tunnel --url http://localhost:8766 --no-autoupdate > /tmp/cf_tunnel.log 2>&1 & echo PID:$!',
    timeout=10
)
print(o.read().decode().strip())

time.sleep(8)

# Check tunnel status
_,o,_ = ssh.exec_command('cat /tmp/cf_tunnel.log 2>/dev/null | head -20', timeout=5)
log = o.read().decode(errors='replace').strip()
print(f'Tunnel log: {log[:500]}')

# If tunnel is running, extract the URL
_,o,_ = ssh.exec_command(
    'grep -o "https://[a-z0-9.-]*\.trycloudflare\.com" /tmp/cf_tunnel.log 2>/dev/null | head -1',
    timeout=5
)
url = o.read().decode().strip()
print(f'Tunnel URL: {url or "not found yet"}')

# Also start a background tunnel
_,o,_ = ssh.exec_command(
    'cat /tmp/cf_tunnel.log 2>/dev/null | grep -o "https://.*\.trycloudflare\.com" | head -1',
    timeout=5
)
url2 = o.read().decode().strip()
print(f'Try2 URL: {url2 or "not found"}')

ssh.close()
