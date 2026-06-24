import paramiko, json, sys

host, user, pw = '122.51.144.227', 'ubuntu', 'Hj711201'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=user, password=pw, timeout=10)

# Check OCR import
cmd = (
    'cd /home/ubuntu/my-evo-ai && python3 -c "'
    'import sys; sys.path.insert(0,\".\"); '
    'try:'
    ' from api.routes.routes_ocr import router; '
    ' print(\"OK\",router.prefix,len(router.routes))'
    'except Exception as e:'
    ' print(\"ERR\",str(e)[:200])'
    '" 2>&1'
)
stdin, stdout, stderr = c.exec_command(cmd)
out = stdout.read().decode('utf-8', 'replace').strip()
err = stderr.read().decode('utf-8', 'replace').strip()
print('OCR:', out)
if err:
    print('STDERR:', err[:200])

# Also check routes_ocr.py imports from modules
cmd2 = (
    'cd /home/ubuntu/my-evo-ai && python3 -c "'
    'import sys; sys.path.insert(0,\".\"); '
    'try:'
    ' from modules import ocr_engine; '
    ' print(\"OK\",hasattr(ocr_engine,\"recognize_image\"))'
    'except Exception as e:'
    ' print(\"ERR\",str(e)[:200])'
    '" 2>&1'
)
stdin2, stdout2, stderr2 = c.exec_command(cmd2)
out2 = stdout2.read().decode('utf-8', 'replace').strip()
print('OCR_ENGINE:', out2)

c.close()
print('DONE')
