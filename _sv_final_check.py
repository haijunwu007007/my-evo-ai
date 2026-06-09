"""Final HTTPS status check"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=30)

def run(cmd, t=10):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(1)
    r = b''
    while o.channel.recv_ready():
        r += o.channel.recv(4096)
    return r.decode(errors='replace').strip()[:500]

print('1.Cert:', run('ls -la /etc/nginx/selfsigned.crt /etc/nginx/selfsigned.key', 5))
print('2.Nginx:', run('sudo nginx -t 2>&1', 8))
print('3.Ports:', run("ss -tlnp | grep -E '80|443'", 5))
print('4.Local:', run('curl -sk https://127.0.0.1/api/v1/version', 10))
print('5.Public:', run('curl -sk --connect-timeout 5 https://122.51.144.227/api/v1/version 2>&1', 10))

# Test external
import httpx
try:
    r = httpx.get('http://122.51.144.227/', timeout=10, follow_redirects=False)
    print(f'6.HTTP: status={r.status_code} location={r.headers.get("location","")[:50]}')
except Exception as e:
    print(f'6.HTTP: {str(e)[:80]}')

ssh.close()
print('DONE')
