#!/bin/bash
# AUTO-EVO-AI 健康检查告警脚本
# 每5分钟检查服务是否在线，失败时通知

URL="http://localhost:8765/api/v1/status"
NOTIFY_URL=""  # 可配置钉钉/飞书Webhook

STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$URL" 2>/dev/null)
if [ "$STATUS" != "200" ]; then
  echo "[ALERT] 服务异常: HTTP $STATUS at $(date)"
  # 尝试重启
  cd /home/ubuntu/my-evo-ai && nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 &
else
  echo "[OK] 服务正常 ($(date))"
fi
