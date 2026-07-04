import urllib.request
r = urllib.request.urlopen("https://autoevoai.com/frontend/chat_engine.js?v=21", timeout=10)
js = r.read().decode("utf-8")

# Find showLoading
i = js.find("showLoading")
if i < 0: i = js.find("show_loading")
print("showLoading at:", i)
if i >= 0:
    print(js[i:i+300])

# Find how the thinking message is rendered
j = js.find("addMsg")
print("\naddMsg appearances:")
idx = 0
while True:
    idx = js.find("addMsg", idx)
    if idx < 0: break
    print(f"  {idx}: {js[idx:idx+100]}")
    idx += 1
