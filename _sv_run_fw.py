"""Check credentials and run firewall script on server"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# SCP the firewall script
sftp = ssh.open_sftp()
sftp.put('D:\\AUTO-EVO-AI-V0.1\\_sv_check_creds.py', '/home/ubuntu/check_creds.py')
sftp.put('/home/ubuntu/fw_add_443.py', '/home/ubuntu/fw_add_443.py')
sftp.close()

# Check env secrets
stdin,stdout,stderr = ssh.exec_command('env | grep -i secret', timeout=5)
print('ENV:', stdout.read().decode(errors='replace').strip()[:300])

# Check credentials files
stdin,stdout,stderr = ssh.exec_command('cat /etc/tencentcloud/credentials 2>/dev/null; cat ~/.tencentcloud/credentials 2>/dev/null; cat /root/.tencentcloud/credentials 2>/dev/null', timeout=5)
print('CRED:', stdout.read().decode(errors='replace').strip()[:500])

# Check CAM metadata
stdin,stdout,stderr = ssh.exec_command('curl -s http://metadata.tencentyun.com/latest/meta-data/cam/security-credentials/', timeout=5)
print('CAM:', stdout.read().decode(errors='replace').strip()[:200])

# Run firewall script
stdin,stdout,stderr = ssh.exec_command('python3 /home/ubuntu/fw_add_443.py', timeout=15)
print('FW:', stdout.read().decode(errors='replace').strip()[:500])
print('FW_ERR:', stderr.read().decode(errors='replace').strip()[:300])

ssh.close()
print('DONE')
