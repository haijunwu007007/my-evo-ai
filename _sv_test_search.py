"""Test simple tool and search on server"""
import paramiko, time, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('122.51.144.227', username='ubuntu', password='EvoAi2024!', timeout=15)

# Test 1: "搜索Python" with 180s timeout
tests = [
    ("搜索Python", 180),
    ("画一朵花", 120),
    ("你好呀", 60),
]
for msg, timeout in tests:
    cmd = f'curl -s -X POST http://127.0.0.1:8766/api/v1/smart -H "Content-Type: application/json" -d \'{{"message":"{msg}"}}\' --max-time {timeout}'
    try:
        _,o,_ = ssh.exec_command(cmd, timeout=timeout+10)
        out = o.read().decode(errors='replace')
        try:
            d = json.loads(out)
            print(f"[{msg}] MODE={d.get('mode','?')} time={timeout}s result={str(d.get('result',''))[:200]}")
        except:
            print(f"[{msg}] RAW={out[:200]}")
    except Exception as e:
        print(f"[{msg}] ERROR={e}")

ssh.close()
print("DONE")
