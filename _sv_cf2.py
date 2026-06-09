"""Fix cloudflared install"""
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

# Check what was downloaded
print('CHECK:', run('file /usr/local/bin/cloudflared 2>/dev/null; head -3 /usr/local/bin/cloudflared 2>/dev/null; ls -la /usr/local/bin/cloudflared 2>/dev/null', 5))

# Try apt install instead
print('APT:', run('sudo apt-get install -y cloudflared 2>&1 | tail -5', 120))

# OR pip install
print('PIP:', run('pip3 install cloudflared 2>&1 | tail -5', 60))

# Check result
print('VER:', run('cloudflared version 2>&1', 10))
print('WHICH:', run('which cloudflared 2>&1', 5))

# If pip installed, check where
print('PIP LOC:', run('python3 -m cloudflared --help 2>&1 | head -3', 10))

ssh.close()
