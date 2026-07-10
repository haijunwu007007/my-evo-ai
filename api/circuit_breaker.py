"""熔断器"""
import logging
logger = logging.getLogger("evo.circuit_breaker")

import os, time, threading

class CircuitBreaker:
    def __init__(self, name, threshold=3, recovery=60):
        self.name = name; self.threshold = threshold
        self.recovery = recovery; self.failures = 0
        self.last_fail = 0; self.state = "closed"
        self.lock = threading.Lock()
    def call(self, func, *a, **kw):
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_fail > self.recovery:
                    self.state = "half-open"
                else:
                    return {"ok": False, "data": f"熔断: {self.name}"}
        try:
            r = func(*a, **kw)
            with self.lock:
                self.failures = 0; self.state = "closed"
            return r
        except Exception as e:
            with self.lock:
                self.failures += 1; self.last_fail = time.time()
                if self.failures >= self.threshold:
                    self.state = "open"
            return {"ok": False, "data": f"失败({self.name}): {str(e)}"}

BREAKERS = {}
def get_breaker(name):
    if name not in BREAKERS:
        BREAKERS[name] = CircuitBreaker(name)
    return BREAKERS[name]
