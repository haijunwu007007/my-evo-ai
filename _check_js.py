import urllib.request
r = urllib.request.urlopen("https://autoevoai.com/frontend/chat_engine.js?v=21", timeout=10)
js = r.read().decode("utf-8")
print("chat_engine.js:", len(js), "bytes")

# Find send function
i = js.find("function send")
if i < 0: i = js.find("send=function")
print("\nsend function start at:", i)
if i >= 0:
    print(js[i:i+500])
else:
    # search for thinking indicator
    for kw in ["思考", "thinking", "input.value", ".value=", "color", "style"]:
        j = js.find(kw)
        if j >= 0:
            print(f"\n'{kw}' at {j}:")
            print(js[max(0,j-50):j+100])
