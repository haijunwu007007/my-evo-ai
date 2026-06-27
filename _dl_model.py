import urllib.request, os, sys, time

url = 'https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip'
local = r'C:\Users\吴海军\Downloads\vosk-cn.zip'

print(f'Downloading {url}...')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=300)
total = int(resp.headers.get('Content-Length', 0))
downloaded = 0
with open(local, 'wb') as f:
    while True:
        chunk = resp.read(8192)
        if not chunk:
            break
        f.write(chunk)
        downloaded += len(chunk)
        pct = downloaded * 100 // total if total else 0
        mb = downloaded / 1024 / 1024
        print(f'\r  {mb:.1f}MB / {total/1024/1024:.0f}MB ({pct}%)', end='', flush=True)

print(f'\nDownloaded: {os.path.getsize(local)} bytes')
