"""多Worker支持 + 超时熔断"""
import os, time, json, threading
from functools import wraps

# Worker 配置
WORKERS = int(os.environ.get("EVO_WORKERS", "4"))
TIMEOUT_SECONDS = int(os.environ.get("EVO_TOOL_TIMEOUT", "60"))

def get_worker_count():
    return WORKERS

# ── 熔断器 ──

class CircuitBreaker:
    def __init__(self, name, failure_threshold=5, recovery_timeout=30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed / open / half-open
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half-open"
                else:
                    return {"ok": False, "data": f"熔断器已开启({self.name})，请稍后重试"}

        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.failure_count = 0
                if self.state == "half-open":
                    self.state = "closed"
            return result
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
            return {"ok": False, "data": f"工具执行失败({self.name}): {str(e)}"}

circuit_breakers = {}

def get_circuit_breaker(name):
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name)
    return circuit_breakers[name]

# ── 超时装饰器 ──

def with_timeout(timeout=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]

            def worker():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            t.join(timeout=timeout)

            if t.is_alive():
                return {"ok": False, "data": f"执行超时({timeout}s)"}
            if error[0]:
                return {"ok": False, "data": f"执行失败: {error[0]}"}
            return result[0]
        return wrapper
    return decorator
