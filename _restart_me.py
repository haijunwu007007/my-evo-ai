#!/usr/bin/env python3
"""在服务器上执行此脚本重启API服务"""
import os, time
os.system("pkill -f api_server 2>/dev/null")
time.sleep(2)
os.chdir("/home/ubuntu/my-evo-ai")
os.system("nohup python3 api_server.py --port 8765 > /tmp/evo_api.log 2>&1 &")
print("RESTART_OK")
