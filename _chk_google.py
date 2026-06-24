import urllib.request
for u in ["http://www.google.com","http://www.baidu.com"]:
    try:
        r=urllib.request.urlopen(u,timeout=5)
        print(u,"OK",r.status)
    except Exception as e:
        print(u,"ERR",str(e)[:50])
