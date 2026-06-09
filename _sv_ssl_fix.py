"""Fix HTTPS: install certbot + Let's Encrypt SSL"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# 1. Install certbot
print("Installing certbot...")
_,o1,_ = ssh.exec_command('sudo apt-get update -qq && sudo apt-get install -y -qq certbot python3-certbot-nginx 2>&1 | tail -5', timeout=120)
print(o1.read().decode()[:300])

# 2. Get SSL cert
print("Getting SSL cert...")
_,o2,_ = ssh.exec_command('sudo certbot --nginx -d autoevoai.com --non-interactive --agree-tos --email admin@autoevoai.com 2>&1', timeout=120)
out = o2.read().decode()
print(out[:500])

# 3. Check result
_,o3,_ = ssh.exec_command('sudo nginx -t 2>&1', timeout=10)
print("NGINX:", o3.read().decode()[:200])

_,o4,_ = ssh.exec_command('ss -tlnp | grep -E "443|80"', timeout=10)
print("PORTS:", o4.read().decode()[:300])

# 4. Test HTTPS
_,o5,_ = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" https://autoevoai.com/api/v1/version --max-time 10', timeout=15)
print("HTTPS:", o5.read().decode().strip())

ssh.close()
