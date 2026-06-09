"""Fix and start cloudflared"""
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
    return r.decode(errors='replace').strip()[:800]

# Kill any stuck process
print('KILL:', run('sudo systemctl stop cloudflared 2>&1; sudo killall cloudflared 2>/dev/null; sleep 1; echo OK', 10))

# Verify binary works
print('VER:', run('/usr/local/bin/cloudflared version 2>&1', 10))

# Start fresh
print('START:', run('sudo systemctl start cloudflared 2>&1', 10))
time.sleep(5)

# Check logs for URL
print('LOG:', run('sudo journalctl -u cloudflared --no-pager -n 30 2>&1', 10))

# Also get URL from trycloudflare
print('TRY:', run('sudo journalctl -u cloudflared --no-pager 2>&1 | grep -i "trycloudflare\\|url\\|https"', 10))

ssh.close()
