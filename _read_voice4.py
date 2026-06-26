import urllib.request
d = urllib.request.urlopen("http://122.51.144.227:8765/frontend/chat_engine.js", timeout=15).read().decode()
p = d.find("if(_voiceMediaRec&&_voiceChunks.length>0)")
if p >= 0:
    raw = d[p:p+700]
    # Replace non-ASCII with ?
    safe = raw.encode("ascii", "replace").decode("ascii")
    print(safe[:600])
