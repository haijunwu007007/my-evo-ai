"""检查服务完整日志"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='Hj711201', timeout=15)

si,so,se = ssh.exec_command("sudo journalctl -u evo.service --no-pager -n 100 2>&1", timeout=15)
out = so.read().decode(errors='replace')
print(out)
ssh.close()
