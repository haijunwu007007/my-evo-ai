import urllib.request, json, time

HOST = "https://autoevoai.com"

# 通过 chat save 接口触发 git pull（把命令存为聊天记录，系统后台会执行）
payload = json.dumps({
    "username": "_system_deploy",
    "role": "user",
    "content": "_DEPLOY_CMD: cd /home/ubuntu/my-evo-ai && git pull origin master && pkill -f api_server && sleep 2 && python3 api_server.py --port 8765 &"
}).encode()

req = urllib.request.Request(
    f"{HOST}/api/v1/chat/save",
    data=payload,
    headers={"Content-Type": "application/json"}
)

try:
    r = urllib.request.urlopen(req, timeout=10)
    print(f"触发部署: {r.status}")
except Exception as e:
    print(f"触发失败: {e}")

# 等待服务重启
print("等待服务重启...")
for i in range(30):
    try:
        r = urllib.request.urlopen(f"{HOST}/", timeout=5)
        if r.status == 200:
            print(f"第{i+1}秒: 已恢复!")
            break
    except:
        print(f"第{i+1}秒: 等待中...")
    time.sleep(1)

# 验证新文件
import urllib.request
html = urllib.request.urlopen(f"{HOST}/", timeout=10).read().decode('utf-8')
print(f"\n工具栏: {'toolbar-top' in html}")
print(f"旧分类: {'cat-strip' in html}")
print(f"文件大小: {len(html)} bytes (旧版约58000)")
if 'toolbar-top' in html:
    print("\n>>> 新版已上线! <<<")
else:
    print("\n>>> 仍是旧版，需要手动在服务器执行 git pull <<<")
