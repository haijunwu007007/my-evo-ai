import paramiko
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect("122.51.144.227", username="ubuntu", password="Hj711201", timeout=10)

# Check if any of our module names exist as top-level files
stdin, stdout, stderr = s.exec_command("cd /home/ubuntu/my-evo-ai && python3 -c \"import sys; import os; wd=os.getcwd(); [print(p) for p in sys.path[:10]]\" 2>&1")
print("PYTHONPATH:", stdout.read().decode()[:200])

# Check for file name collisions in project root
stdin, stdout, stderr = s.exec_command("ls /home/ubuntu/my-evo-ai/*.py 2>/dev/null | grep -E 'qodo|testsigma|dagger|airbyte|grafana|sentry|docling|invoice|chatwoot|postiz|cal'")
result = stdout.read().decode().strip()
if result:
    print("CONFLICTING FILES:", result)
else:
    print("NO top-level conflicts")

# Check __init__.py for module scanning
stdin, stdout, stderr = s.exec_command("cd /home/ubuntu/my-evo-ai && python3 -c \"from modules.qodo_review import __name__; print(__name__)\"")
print("MODULE PATH:", stdout.read().decode()[:100])

stdin, stdout, stderr = s.exec_command("cd /home/ubuntu/my-evo-ai && python3 -c \"import qodo_review as m; print(m.__file__)\"")
print("TOP-LEVEL:", stdout.read().decode()[:200])
print("ERR:", stderr.read().decode()[:200])

s.close()
