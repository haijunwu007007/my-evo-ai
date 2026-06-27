import requests, json, struct, io, re, warnings
warnings.filterwarnings('ignore')

print('=== API Status ===')
r = requests.get('https://autoevoai.com/api/status', verify=False, timeout=15)
print(r.status_code, json.dumps(r.json(), ensure_ascii=False)[:100])

print('\n=== Speech Status ===')
r2 = requests.get('https://autoevoai.com/api/v1/speech/status', verify=False, timeout=15)
print(json.dumps(r2.json(), ensure_ascii=False))

print('\n=== Chat Version ===')
r3 = requests.get('https://autoevoai.com/frontend/chat.html', verify=False, timeout=15)
v = re.findall(r'v=(\d+)', r3.text)
print('v=', v)
print('has SW reg:', 'serviceWorker' in r3.text)
print('has voiceMic:', 'voiceMic' in r3.text)
print('size:', len(r3.text))

print('\n=== Engine Test ===')
sr=16000; n=int(sr*1)
wav = io.BytesIO()
import wave as w
with w.open(wav,'wb') as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
    f.writeframes(b''.join(struct.pack('<h',int(16000*(1+i%100/100))) for i in range(n)))
wav.seek(0)
r4 = requests.post('https://autoevoai.com/api/v1/speech/recognize',
    files={'file': ('v.wav', wav, 'audio/wav')}, verify=False, timeout=120)
print(json.dumps(r4.json(), ensure_ascii=False)[:200])

print('\n=== All tests done ===')
