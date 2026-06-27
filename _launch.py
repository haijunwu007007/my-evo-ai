import os, subprocess, sys
os.environ['EVO_WORKERS'] = '1'
os.environ['EVO_PORT'] = '8766'
proc = subprocess.Popen([sys.executable, 'api_server.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
print(f'Started PID {proc.pid} on port 8766')
