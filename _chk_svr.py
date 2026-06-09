"""Check server for Tencent Cloud API access"""
import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Check tccli
_,o,_ = ssh.exec_command('which tccli 2>/dev/null; echo "---"; pip3 list 2>/dev/null | grep -i tencent; echo "---"; env | grep -iE "TENCENT|SECRET|API" | head -10', timeout=10)
print('SERVER CHECK:', o.read().decode(errors='replace')[:500])

# Check ufw/iptables
_,o2,_ = ssh.exec_command('sudo ufw status 2>/dev/null; echo "---"; sudo iptables -L INPUT -n --line-numbers 2>/dev/null | head -20', timeout=10)
print('FIREWALL:', o2.read().decode(errors='replace')[:500])

# Check if Tencent Cloud API secret key exists in any config
_,o3,_ = ssh.exec_command('grep -r "secret" /home/ubuntu/.tencent* /home/ubuntu/*.json 2>/dev/null | head -5; echo "---"; ls -la /home/ubuntu/.tencent* 2>/dev/null', timeout=10)
print('SECRETS:', o3.read().decode(errors='replace')[:500])

ssh.close()
print('DONE')
