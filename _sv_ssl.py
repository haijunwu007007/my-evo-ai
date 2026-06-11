import paramiko, time, sys
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='Hj711201', timeout=15, look_for_keys=False, allow_agent=False)
print('SSH_OK')

def run(cmd, t=60):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(1)
    out = b''
    while o.channel.recv_ready():
        out += o.channel.recv(4096)
    return out.decode(errors='replace').strip()[-500:]

# Check certbot
print('Certbot:', run('which certbot 2>&1 || echo NOT_FOUND', 5))
print('Snap:', run('which snap 2>&1 || echo NO_SNAP', 5))

# Check current nginx SSL config  
print('Nginx SSL:', run('grep -A2 "ssl_certificate" /etc/nginx/sites-enabled/evo.conf 2>&1', 5))

# Try install certbot via snap (less dep issues)
print('Trying snap...', run('sudo snap install --classic certbot 2>&1', 60))

# Check certs again
print('Cert after:', run('which certbot 2>&1 || echo FAIL', 5))

ssh.close()
