# AUTO-EVO-AI 生产部署指南

## 部署方式1：systemd（推荐）

```bash
sudo cp deploy/evo-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable evo-api
sudo systemctl start evo-api
# 查看状态
sudo systemctl status evo-api
# 查看日志
sudo journalctl -u evo-api -f
```

## 部署方式2：nohup（快速启动）

```bash
cd ~/my-evo-ai
nohup venv/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &
```

## 日志轮转

```bash
sudo cp deploy/logrotate.conf /etc/logrotate.d/evo-api
sudo logrotate -f /etc/logrotate.d/evo-api
```

## 安全组

腾讯云安全组必须放行 TCP 8765 端口。
