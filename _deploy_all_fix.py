import paramiko, time, os
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', 22, 'ubuntu', 'Hj711201', timeout=30)
sftp = ssh.open_sftp()

# Upload cleaned routes_speech.py
local = r'D:\AUTO-EVO-AI-V0.1\api\routes\routes_speech.py'
remote = '/home/ubuntu/my-evo-ai/api/routes/routes_speech.py'
sftp.put(local, remote)
size = os.path.getsize(local)
sftp.close()
print(f'Uploaded {size} bytes')

# Kill all uvicorn/python processes and restart
si,so,se = ssh.exec_command(
    'sudo systemctl stop evo.service 2>/dev/null; '
    'pkill -9 -f "uvicorn api_server" 2>/dev/null; '
    'sleep 2; '
    'sudo systemctl start evo.service; '
    'sleep 15; '
    'systemctl is-active evo.service',
    timeout=30)
time.sleep(3)
print('Status:', so.read().decode().strip()[:200])

# Verify
import urllib.request, ssl, json
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
time.sleep(5)
try:
    r = urllib.request.urlopen('https://autoevoai.com/api/status', timeout=15, context=ctx)
    data = json.loads(r.read())
    print('API:', data.get('status'), data.get('modules_loaded'))
except Exception as ex:
    print('API error:', ex)

ssh.close()
