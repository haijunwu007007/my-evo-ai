"""
AUTO-EVO-AI 企业级模块增强层
为所有 570 模块注入上市公司标准：重试/熔断/指标/结构化日志/健康检查
"""
import functools, time, logging, traceback
from core.logging_config import get_logger
from typing import Dict, Any, Optional
from collections.abc import Callable

logger = get_logger("enterprise")

# ─── 1. 重试装饰器 ───

def with_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """带指数退避的重试"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if attempt < max_retries:
                        wait = delay * (backoff ** attempt)
                        logger.warning(f"[RETRY] {func.__name__} 第{attempt+1}次失败: {e}，{wait:.1f}s后重试")
                        time.sleep(wait)
            logger.error(f"[RETRY] {func.__name__} 重试{max_retries}次全部失败: {last_err}")
            return {"success": False, "error": str(last_err), "retried": max_retries}
        return wrapper
    return decorator


# ─── 2. 熔断器 ───

class CircuitBreaker:
    """简单熔断器：连续失败 N 次后断开，M 秒后半开尝试"""
    def __init__(self, name: str, threshold: int = 5, recovery_timeout: float = 30.0):
        self.name = name
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.fail_count = 0
        self.last_fail_time = 0.0
        self.state = "closed"  # closed → open → half_open → closed

    def call(self, func: Callable, *args, **kwargs) -> dict:
        now = time.time()
        if self.state == "open":
            if now - self.last_fail_time > self.recovery_timeout:
                self.state = "half_open"
                logger.info(f"[CB] {self.name} 半开，允许试探请求")
            else:
                return {"success": False, "error": f"熔断器已断开({self.fail_count}次失败)", "circuit_breaker": True}
        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.fail_count = 0
                logger.info(f"[CB] {self.name} 恢复正常")
            else:
                self.fail_count = 0
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as e:
            self.fail_count += 1
            self.last_fail_time = now
            if self.fail_count >= self.threshold:
                self.state = "open"
                logger.warning(f"[CB] {self.name} 熔断开启({self.fail_count}次)")
            return {"success": False, "error": str(e)}


# ─── 3. 执行时间度量 ───

def with_metrics(name: str):
    """记录执行时间和结果"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"[METRIC] {name} 完成 {elapsed*1000:.0f}ms")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"[METRIC] {name} 失败 {elapsed*1000:.0f}ms: {e}")
                raise
        return wrapper
    return decorator


# ─── 4. 模块升级器 ───

def upgrade_module(module_code: str, module_name: str) -> str:
    """对企业模块代码注入上市公司级增强"""
    # 添加重试到 execute 方法
    if "def execute" in module_code and "@with_retry" not in module_code:
        module_code = module_code.replace(
            "def execute(",
            "    @with_retry(max_retries=3, delay=1.0, backoff=2.0)\n    def execute("
        )
    # 添加 metrics
    if "def execute" in module_code and "@with_metrics" not in module_code:
        module_code = module_code.replace(
            "def execute(self",
            "@with_metrics('" + module_name + "')\ndef execute(self"
        )
    # 添加 import
    if "from core.module_enterprise import" not in module_code:
        module_code = "from core.module_enterprise import with_retry, with_metrics\n" + module_code
    # 确保返回字典
    for pattern in ["return None", "return []", "return ''", "return 0"]:
        if pattern in module_code and "def execute" in module_code:
            lines = module_code.split('\n')
            for i, line in enumerate(lines):
                if pattern in line and 'execute' in module_code[max(0,i-10):i]:
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    lines[i] = f'{indent}return {{"success": True, "data": {line.strip().replace("return ", "")}}}'
            module_code = '\n'.join(lines)
    return module_code
