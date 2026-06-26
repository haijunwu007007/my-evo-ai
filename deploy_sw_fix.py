#!/usr/bin/env python3
"""Upload SW fix files to server and deploy."""
import paramiko
import os

HOST = '122.51.144.227'
PORT = 22
USER = 'ubuntu'
PASS = 'Hj711201'
REMOTE_ROOT = '/home/ubuntu/my-evo-ai'
LOCAL_ROOT = 'D:/AUTO-EVO-AI-V0.1'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, PASS, timeout=15)
sftp = ssh.open_sftp()

# Files to upload
files = {
    f'{LOCAL_ROOT}/sw.js': f'{REMOTE_ROOT}/sw.js',
    f'{LOCAL_ROOT}/frontend/index_deployed.html': f'{REMOTE_ROOT}/frontend/chat.html',
}

for local, remote in files.items():
    size = os.path.getsize(local)
    print(f'Uploading {local} ({size} bytes) -> {remote}...')
    sftp.put(local, remote)
    print(f'  OK')

# Check chat.html file size
stdin, stdout, stderr = ssh.exec_command('wc -c /home/ubuntu/my-evo-ai/frontend/chat.html')
print(f'\nchat.html size: {stdout.read().decode().strip()}')

# Check sw.js
stdin, stdout, stderr = ssh.exec_command('wc -c /home/ubuntu/my-evo-ai/sw.js')
print(f'sw.js size: {stdout.read().decode().strip()}')

# Restart evo service
print('\nRestarting evo.service...')
stdin, stdout, stderr = ssh.exec_command('echo Hj711201 | sudo -S systemctl restart evo.service 2>&1')
import time
time.sleep(2)

# Check status
stdin, stdout, stderr = ssh.exec_command('systemctl is-active evo.service')
print(f'Service status: {stdout.read().decode().strip()}')

# Verify HTTP
import urllib.request
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://autoevoai.com/')
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
html = resp.read().decode('utf-8', errors='ignore')
if 'v=3' in html and 'serviceWorker' in html:
    print('\nDEPLOY SUCCESS: v=3 and SW registration found in HTML!')
elif 'v=2' in html:
    print('\nWARNING: Still v=2, deploy may not have taken effect')
else:
    print(f'\nResponse: {len(html)} bytes')

sftp.close()
ssh.close()
print('\nDone')
