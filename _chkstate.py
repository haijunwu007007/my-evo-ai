import urllib.request,ssl,sys
sys.stdout.reconfigure(encoding='utf-8')
ctx=ssl.create_default_context();ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
r=urllib.request.urlopen('https://autoevoai.com/',timeout=15,context=ctx);h=r.read().decode()
print('voiceOverlay:',h.count('voiceOverlay'))
print('voiceMic:',h.count('voiceMic'))
print('sbtn:',h.count('sbtn'))
print('Size:',len(h))
i=h.find('voiceMic')
if i>=0: print('Mic:',h[i-5:i+80])
