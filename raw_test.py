import paramiko
C=paramiko.SSHClient()
C.set_missing_host_key_policy(paramiko.AutoAddPolicy())
C.connect('122.51.144.227',port=22,username='ubuntu',password='Hj711201',timeout=10,banner_timeout=60)
# Get raw response
_,o,_=C.exec_command('curl -s -w "\nCODE:%{http_code}" -m 5 http://127.0.0.1:8765/api/v1/hub/discover 2>/dev/null',timeout=10,get_pty=True)
raw=o.read().decode()
print(raw[:500])
print('---')
# Test the company endpoints too
_,o2,_=C.exec_command('curl -s -w "\nCODE:%{http_code}" -m 5 http://127.0.0.1:8765/api/v1/company/status 2>/dev/null',timeout=10,get_pty=True)
print(o2.read().decode()[:500])
C.close()
