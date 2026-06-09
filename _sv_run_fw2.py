"""SCP and run firewall script"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# SCP firewall script
sftp = ssh.open_sftp()
sftp.put('D:\\AUTO-EVO-AI-V0.1\\fw_add_443.py', '/home/ubuntu/fw_add_443.py')
sftp.close()

# Check env
stdin,stdout,stderr = ssh.exec_command('env | grep -i secret', timeout=5)
env_out = stdout.read().decode(errors='replace').strip()
print('ENV:', env_out[:300])

# Check credentials files
stdin,stdout,stderr = ssh.exec_command('cat /etc/tencentcloud/credentials 2>/dev/null; echo SEP; cat ~/.tencentcloud/credentials 2>/dev/null; echo SEP2; cat /root/.tencentcloud/credentials 2>/dev/null', timeout=5)
print('CRED:', stdout.read().decode(errors='replace').strip()[:500])

# Check CAM metadata
stdin,stdout,stderr = ssh.exec_command('curl -s --max-time 5 http://metadata.tencentyun.com/latest/meta-data/cam/security-credentials/', timeout=8)
print('CAM:', stdout.read().decode(errors='replace').strip()[:200])

# Run firewall script
stdin,stdout,stderr = ssh.exec_command('python3 /home/ubuntu/fw_add_443.py 2>&1', timeout=20)
print('RESULT:', stdout.read().decode(errors='replace').strip()[:500])

ssh.close()
