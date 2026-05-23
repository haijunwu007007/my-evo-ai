# 云部署指南

## 方式一：Docker（推荐）

```bash
docker compose up -d
```

访问 http://localhost:8765

## 方式二：内网穿透（手机远程访问）

1. 安装 Cloudflare Tunnel:
   ```bash
   winget install Cloudflare.cloudflared
   ```
2. 回到 Dashboard 点击 🌐 按钮
3. 选择 Cloudflare Tunnel

## 方式三：服务器部署

```bash
# 安装依赖
pip install -r requirements.txt

# 启动
python api_server.py
```

访问 http://你的服务器IP:8765
