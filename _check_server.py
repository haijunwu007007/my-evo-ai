import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('autoevoai.com', username='ubuntu', password='Hj711201', timeout=15)
stdin, stdout, stderr = ssh.exec_command("echo '===CPU==='; nproc; echo '===MEM==='; free -h; echo '===DISK==='; df -h /; echo '===OS==='; head -3 /etc/os-release; echo '===PG==='; dpkg -l postgresql 2>/dev/null | tail -1 || echo 'not installed'")
print(stdout.read().decode())
ssh.close()
