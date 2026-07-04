"""使用 paramiko 部署 chat.html 到公网服务器"""
import paramiko
import base64
import time

HOST = "122.51.144.227"
PORT = 22
USER = "ubuntu"
PASS = "Hj711201"
REMOTE_PATH = "/home/ubuntu/my-evo-ai/frontend/chat.html"

# 读取本地文件
with open("D:/AUTO-EVO-AI-V0.1/frontend/chat.html", "r", encoding="utf-8") as f:
    content = f.read()

print(f"✅ 本地文件: {len(content)} bytes")

# SSH 连接
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, PASS, timeout=15)
print("✅ SSH 连接成功")

# 用 SFTP 直接写文件
sftp = ssh.open_sftp()
with sftp.open(REMOTE_PATH, "w") as f:
    f.write(content)
sftp.close()
print(f"✅ 文件已写入服务器 {REMOTE_PATH}")

# 重启服务
stdin, stdout, stderr = ssh.exec_command("sudo pkill -f 'api_server' 2>/dev/null; echo 'restarted'")
print(f"🔄 服务重启: {stdout.read().decode('utf-8').strip()}")

ssh.close()

# 验证
print("\n⏳ 等待服务恢复...")
import urllib.request
for i in range(15):
    try:
        resp = urllib.request.urlopen("https://autoevoai.com/", timeout=5)
        if resp.status == 200:
            html = resp.read().decode("utf-8")
            print(f"✅ 第{i+1}秒: 服务已恢复! ({len(html)} bytes)")
            if 'rightToggleBtn' in html:
                print("✅ 新版本部署成功！")
            else:
                print("⚠️ 版本异常")
            break
    except Exception as e:
        print(f"⏳ 第{i+1}秒: {e}")
    time.sleep(1)
else:
    print("❌ 服务未恢复")
