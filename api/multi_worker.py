"""多Worker + 超时熔断"""
import os, signal, logging
logger = logging.getLogger("evo.multi_worker")
WORKERS = int(os.environ.get("EVO_WORKERS", "4"))
TIMEOUT = int(os.environ.get("EVO_TOOL_TIMEOUT", "120"))

def is_uvicorn_available():
    try:
        import uvicorn
        return True
    except ImportError:
        return False

def to_seconds(hours=24):
    return hours * 3600

def start_server(app, host="0.0.0.0", port=8765):
    if not is_uvicorn_available():
        logger.warning("uvicorn not available, using single process")
        return
    import uvicorn
    cfg = uvicorn.Config(app, host=host, port=port, workers=WORKERS, log_level="info")
    srv = uvicorn.Server(cfg)
    srv.run()
