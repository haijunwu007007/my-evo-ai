import urllib.request
r = urllib.request.urlopen("https://autoevoai.com/frontend/chat_engine.js?v=21", timeout=10)
js = r.read().decode("utf-8")

# addMsg function
i = js.find("addMsg(")
print("=== addMsg ===")
print(js[i:i+400])

# showLoading - careful
j = js.find("showLoading")
print("\n=== showLoading ===")
print(js[j:j+300])

# hideLoading
k = js.find("hideLoading")
print("\n=== hideLoading ===")
print(js[k:k+150])
