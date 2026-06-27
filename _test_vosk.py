import requests, json, warnings, struct, math, io
warnings.filterwarnings('ignore')

sr = 16000; duration = 2; num = int(sr * duration)
buf = io.BytesIO()
import wave
with wave.open(buf, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    for i in range(num):
        val = int(math.sin(2 * math.pi * 440 * i / sr) * 8000)
        buf.write(struct.pack('<h', val))
wav_bytes = buf.getvalue()

# Upload as WAV
r = requests.post('https://autoevoai.com/api/v1/speech/recognize',
    files={'file': ('voice.wav', wav_bytes, 'audio/wav')},
    verify=False, timeout=30)
print('Recognize result:', json.dumps(r.json(), ensure_ascii=False))
