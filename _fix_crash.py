import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)

# 检查进程状态
si,so,se = ssh.exec_command("ps aux | grep python3 | grep -v grep | grep -v streamlit | grep -v networkd | grep -v unattended", timeout=5)
time.sleep(2)
procs = so.read().decode().strip()
print('Python processes:')
print(procs if procs else 'NONE')

# 检查端口
si2,so2,se2 = ssh.exec_command("ss -tlnp | grep 8765", timeout=5)
time.sleep(1)
print('\nPort 8765:')
print(so2.read().decode().strip() if so2.read().decode().strip() else 'NOT LISTENING!')

# 如果进程挂了，重启
if 'uvicorn' not in procs:
    print('\nUVICORN NOT RUNNING! Restarting...')
    si3,so3,se3 = ssh.exec_command('sudo systemctl restart evo.service', timeout=15)
    time.sleep(8)
    si4,so4,se4 = ssh.exec_command('systemctl is-active evo.service', timeout=5)
    time.sleep(1)
    print('Service:', so4.read().decode().strip())
    si5,so5,se5 = ssh.exec_command("ps aux | grep uvicorn | grep -v grep", timeout=5)
    time.sleep(2)
    print(so5.read().decode().strip()[:200] if so5.read().decode().strip() else 'STILL NOT RUNNING')

ssh.close()
