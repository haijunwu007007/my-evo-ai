@echo off
cd /d D:\AUTO-EVO-AI-V0.1
set EVO_WORKERS=1
set EVO_PORT=8766
start /b python api_server.py
