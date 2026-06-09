"""Deploy + test search"""
import paramiko, time, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

sftp = ssh.open_sftp()
with open(r'D:\AUTO-EVO-AI-V0.1\api\agent_core.py', 'rb') as f:
    c = f.read()
with sftp.open('/home/ubuntu/my-evo-ai/api/agent_core.py', 'wb') as f:
    f.write(c)
sftp.close()
print(f'SCP agent_core.py: {len(c)}b')

ssh.exec_command('sudo systemctl restart evo.service', timeout=30)
time.sleep(6)

# Test search - use single quotes for json
cmd = 'curl -s -X POST http://127.0.0.1:8766/api/v1/smart -H "Content-Type: application/json" -d \'{"message":"搜索Python最新版本"}\' --max-time 120'
_,o,_ = ssh.exec_command(cmd, timeout=125)
out = o.read().decode(errors='replace')
try:
    d = json.loads(out)
    print(f'SEARCH MODE={d.get("mode","?")}')
    print(f'RESULT={str(d.get("result",""))[:600]}')
except:
    print(f'RAW={out[:300]}')

ssh.close()
print('DONE')
