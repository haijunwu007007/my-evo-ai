import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# 看端口
si,so,se = ssh.exec_command("ss -tlnp 2>/dev/null | grep -E '8765|443|80'", timeout=5)
time.sleep(2)
print('Ports:')
print(so.read().decode().strip()[:300])

# 本地 curl 测试
si2,so2,se2 = ssh.exec_command("curl -s --max-time 5 http://127.0.0.1:8765/api/status 2>&1", timeout=10)
time.sleep(5)
print('\nCurl test:')
print(so2.read().decode().strip()[:200] if so2.read().decode().strip() else 'NO RESPONSE')
print(se2.read().decode().strip()[:200] if se2.read().decode().strip() else '')

# 看日志尾
si3,so3,se3 = ssh.exec_command("sudo journalctl -u evo.service --no-pager -n 20 2>&1 | tail -20", timeout=10)
time.sleep(2)
print('\nJournal:')
print(so3.read().decode().strip()[:500])
print(se3.read().decode().strip()[:200])

ssh.close()
