@echo off
REM AUTO-EVO-AI 服务器部署 (Windows Batch)
REM 用法: 双击运行，或 cmd 下执行

echo ==========================================
echo   AUTO-EVO-AI 服务器部署
echo ==========================================

set SSH_KEY=C:\Users\吴海军\.ssh\Myevoaikey_
set SSH_USER=ubuntu
set SSH_HOST=122.51.144.227
set REMOTE_DIR=~/my-evo-ai

echo [1/4] 拉取代码...
ssh -o StrictHostKeyChecking=no -i "%SSH_KEY%" %SSH_USER%@%SSH_HOST% "cd %REMOTE_DIR% && git pull origin master"

echo [2/4] 安装依赖...
ssh -o StrictHostKeyChecking=no -i "%SSH_KEY%" %SSH_USER%@%SSH_HOST% "cd %REMOTE_DIR% && source venv/bin/activate && pip install python-docx python-pptx PyPDF2 pdfplumber openpyxl SpeechRecognition pydub imageio-ffmpeg -q"

echo [3/4] 重启服务...
ssh -o StrictHostKeyChecking=no -i "%SSH_KEY%" %SSH_USER%@%SSH_HOST% "cd %REMOTE_DIR% && pgrep -f uvicorn | xargs kill -9 2>/dev/null; sleep 1; nohup bash start.sh > /tmp/evo.log 2>&1 & sleep 3 && echo 'OK'"

echo [4/4] 验证...
ssh -o StrictHostKeyChecking=no -i "%SSH_KEY%" %SSH_USER%@%SSH_HOST% "curl -s http://localhost:8765/api/v1/health | head -c 200"

echo ==========================================
echo   部署完成!
echo   办公套件: http://122.51.144.227:8765/office
echo ==========================================
pause
