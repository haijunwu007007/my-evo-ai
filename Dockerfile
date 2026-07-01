# AUTO-EVO-AI V0.1 — Docker 镜像
# 构建: docker build -t auto-evo-ai .
# 运行: docker run -d -p 8765:8765 auto-evo-ai

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（Vosk OCR + 截图等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 确保启动入口存在
RUN test -f api_server.py || (echo "ERROR: api_server.py not found" && exit 1)

# 端口
EXPOSE 8765

# 启动
CMD ["python3", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8765"]
