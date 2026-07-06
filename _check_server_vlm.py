import json, urllib.request

H = 'https://autoevoai.com'
def run(cmd):
    p = json.dumps({'cmd': cmd}).encode()
    r = urllib.request.urlopen(urllib.request.Request(H+'/api/v1/cli/exec', data=p, headers={'Content-Type':'application/json'}), timeout=30)
    return json.loads(r.read())

# Check Ollama
r = run("which ollama && ollama --version 2>&1 || echo 'no_ollama'")
print('Ollama:', r.get('stdout','')[:200])

# Check current models
r = run("ollama list 2>&1 || echo 'no_models'")
print('Models:', r.get('stdout','')[:500])

# Check GPU
r = run("nvidia-smi --query-gpu=gpu_name,memory.total,memory.free --format=csv,noheader 2>&1 || echo 'no_gpu'")
print('GPU:', r.get('stdout','')[:300])

# Check RAM
r = run("free -h 2>&1 | head -3")
print('RAM:', r.get('stdout','')[:200])

# Check disk
r = run("df -h / 2>&1 | tail -1")
print('Disk:', r.get('stdout','')[:200])

# Check Ollama API
r = run("curl -s http://localhost:11434/api/tags 2>&1 | head -c 300 || echo 'ollama_api_down'")
print('Ollama API:', r.get('stdout','')[:300])
