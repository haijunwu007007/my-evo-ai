FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
EXPOSE 8765
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8765"]
