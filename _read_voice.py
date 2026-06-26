import urllib.request
d = urllib.request.urlopen("http://122.51.144.227:8765/frontend/chat_engine.js", timeout=15).read().decode()
# Find voice functions
p = d.find("function startVoiceRecord")
if p >= 0:
    print(d[p:p+600])
