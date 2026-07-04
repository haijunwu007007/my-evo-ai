"""等待服务器重启并测试/agents"""
import urllib.request, urllib.error, time

for i in range(30):
    try:
        r = urllib.request.urlopen("https://autoevoai.com/", timeout=5)
        print(f"[{i+1}s] Server UP")
        # Now test /agents
        try:
            r2 = urllib.request.urlopen("https://autoevoai.com/agents", timeout=5)
            print(f"/agents -> {r2.status} loc={r2.headers.get('location','')}")
        except urllib.error.HTTPError as e:
            print(f"/agents -> {e.code} loc={e.headers.get('location','')}")
        break
    except urllib.error.HTTPError as e:
        if e.code == 502:
            pass
        time.sleep(1)
    except:
        time.sleep(1)
