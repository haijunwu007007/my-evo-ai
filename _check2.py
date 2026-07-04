import urllib.request
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
h = r.read().decode("utf-8")
# Find the HTML between <div class="left-panel"> and </div> of input-area
idx = h.find("com/logo")
if idx == -1:
    idx = h.find("双栏")
print("idx:", idx)
print(h[idx:idx+800])
