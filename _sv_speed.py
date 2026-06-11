import paramiko, time, os
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='Hj711201', timeout=15, look_for_keys=False, allow_agent=False)

def run(cmd, t=15):
    _,o,_ = ssh.exec_command(cmd, timeout=t)
    time.sleep(0.3)
    out=b''
    while o.channel.recv_ready(): out+=o.channel.recv(4096)
    return out.decode(errors='replace').strip()[-600:]

# 读取本地修改后的agent_llm.py
local = open(r'D:\AUTO-EVO-AI-V0.1\api\agent_llm.py', 'rb').read()

# SCP到服务器
sftp = ssh.open_sftp()
sftp.putfo(open(r'D:\AUTO-EVO-AI-V0.1\api\agent_llm.py', 'rb'), '/home/ubuntu/my-evo-ai/api/agent_llm.py')
sftp.close()
print('SCP OK')

# 重启服务
print(run('sudo systemctl restart evo.service 2>&1'))
time.sleep(3)
print(run('curl -s http://127.0.0.1/api/v1/version 2>&1', 5))

ssh.close()
print('DONE')
