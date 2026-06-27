import requests,warnings,json,struct,math,io,wave
warnings.filterwarnings('ignore')

r=requests.get('https://autoevoai.com/api/v1/speech/status',verify=False,timeout=15)
print('STATUS:',json.dumps(r.json(),ensure_ascii=False))

sr=16000;dur=1
buf=io.BytesIO()
with wave.open(buf,'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr)
    for i in range(sr*dur):
        w.writeframes(struct.pack('<h',int(math.sin(2*math.pi*440*i/sr)*16383)))
wb=buf.getvalue()

r2=requests.post('https://autoevoai.com/api/v1/speech/recognize',
    files={'file':('v.webm',wb,'audio/webm')},verify=False,timeout=120)
print('RECOG:',json.dumps(r2.json(),ensure_ascii=False))
