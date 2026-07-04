import urllib.request
r = urllib.request.urlopen("https://autoevoai.com/", timeout=10)
html = r.read().decode("utf-8")
print(f"问候语(你好): {'你好' in html}")
print(f"快捷卡片(quick-start): {'quick-start' in html}")
print(f"建议气泡(suggestions): {'suggestions' in html}")
print(f"分类条(cat-strip): {'cat-strip' in html}")
print(f"cat-body全部隐藏: {'cat-body style=\"display:none\"' in html}")
