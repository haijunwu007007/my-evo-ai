"""MinIO - AUTO-EVO-AI集成 (localhost:9000)"""
import json, httpx, os

MINIO_URL = os.environ.get("MINIO_URL", "http://localhost:9000")
MINIO_ACCESS = os.environ.get("MINIO_ACCESS_KEY", "evo_admin")
MINIO_SECRET = os.environ.get("MINIO_SECRET_KEY", "EvoAi2024!")

def minio_storage(**kwargs):
    """MinIO对象存储操作"""
    try:
        action = kwargs.get("action", "list_buckets")
        # Health check
        if action == "health":
            resp = httpx.get(f"{MINIO_URL}/minio/health/live", timeout=5)
            return {"ok": resp.status_code == 200, "data": {"status": "healthy" if resp.status_code == 200 else "unhealthy"}, "message": f"HTTP {resp.status_code}"}
        # List buckets via S3 API
        from minio import Minio
        client = Minio(MINIO_URL.replace("http://", "").replace("https://", ""),
                       access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)
        buckets = client.list_buckets()
        return {"ok": True, "data": [{"name": b.name, "created": str(b.creation_date)} for b in buckets], "message": f"找到{len(buckets)}个存储桶"}
    except ImportError:
        return {"ok": False, "data": None, "message": "minio Python包未安装 (pip install minio)"}
    except httpx.ConnectError:
        return {"ok": False, "data": None, "message": "无法连接MinIO (localhost:9000)，请确认Docker容器已启动"}
    except Exception as e:
        return {"ok": False, "data": None, "message": f"MinIO失败: {e}"}
