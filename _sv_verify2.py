"""Verify public server - run on server side via SSH"""
import paramiko, time, json, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

time.sleep(3)

# Version
_,o,_ = ssh.exec_command('curl -s http://127.0.0.1:8766/api/v1/version --max-time 5', timeout=10)
ver = o.read().decode().strip()
print(f"VERSION: {ver[:200]}")

# Chat
_,o2,_ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8766/api/v1/smart'
    ' -H "Content-Type: application/json"'
    " -d '{\"message\":\"你好\"}'"
    ' --max-time 30', timeout=35)
r2 = o2.read().decode()
try:
    d2 = json.loads(r2)
    print(f"CHAT: mode={d2.get('mode')} result={d2.get('result','')[:80]}")
except:
    print(f"CHAT ERR: {r2[:300]}")

# HTTPS
_,o3,_ = ssh.exec_command(
    'curl -s -o /dev/null -w "%{http_code}" https://autoevoai.com/api/v1/version --max-time 10', timeout=15)
print(f"HTTPS: {o3.read().decode().strip()}")

ssh.close()
