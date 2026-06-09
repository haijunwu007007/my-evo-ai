"""Check logs on server for tool call rounds"""
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Get logs in one shot
_,o,_ = ssh.exec_command('sudo journalctl -u evo.service --no-pager -n 200 2>&1 | grep chat/completions | tail -10', timeout=10)
print("DEEPSEEK CALLS:")
print(o.read().decode(errors='replace')[:1000])

_,o2,_ = ssh.exec_command('sudo journalctl -u evo.service --no-pager -n 200 2>&1 | grep "tool_round\|force\|搜索\|web_search" | tail -10', timeout=10)
print("\nROUNDS:")
print(o2.read().decode(errors='replace')[:1000])

ssh.close()
print("DONE")
