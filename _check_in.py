import urllib.request
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
h = r.read().decode("utf-8")
i = h.find('id="input"')
print("INPUT element:")
print(h[i:i+250])
print()
# Also check for "思考" thinking status
j = h.find("思考")
print("思考 context:")
print(h[max(0,j-100):j+100])
