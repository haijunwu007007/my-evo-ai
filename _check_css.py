import urllib.request
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
h = r.read().decode("utf-8")

# Check for ::root or :root
i = h.find("::root")
if i < 0: i = h.find(":root")
print("CSS root section:")
if i >= 0:
    print(h[i:i+300])
else:
    print("no :root found")

# Check for dark mode
i = h.find("dark")
print("\n'dark' in page:", i)
if i >= 0:
    print(h[max(0,i-50):i+200])
