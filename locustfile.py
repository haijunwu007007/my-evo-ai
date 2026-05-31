"""
AUTO-EVO-AI V0.1 — Locust 性能压测脚本
=======================================
使用: locust -f locustfile.py --host=http://127.0.0.1:8765
Web UI: http://localhost:8089

模拟场景:
  - 管理员浏览仪表盘 (50% 权重)
  - 普通用户浏览模块列表 (30% 权重)
  - 系统状态检查 (20% 权重)
"""

from locust import HttpUser, task, between
import json


class EvoApiUser(HttpUser):
    """模拟 EVO 系统 API 用户的并发行为。"""
    wait_time = between(0.5, 3.0)  # 用户操作间隔 0.5~3 秒

    def on_start(self):
        """每个虚拟用户启动时先登录获取 token。"""
        resp = self.client.post("/api/auth/login", json={"username": "admin"})
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}

    @task(5)
    def system_status(self):
        """查看系统状态（高频端点）。"""
        with self.client.get("/api/status", headers=self.headers, catch_response=True, name="/api/status") as resp:
            if resp.status_code != 200:
                resp.failure(f"Status returned {resp.status_code}")

    @task(3)
    def list_modules(self):
        """列出所有模块。"""
        with self.client.get("/api/modules", headers=self.headers, catch_response=True, name="/api/modules") as resp:
            if resp.status_code != 200:
                resp.failure(f"Modules returned {resp.status_code}")
            else:
                data = resp.json()
                modules = data.get("modules", data.get("data", []))
                if isinstance(modules, list) and len(modules) > 0:
                    # 随机选一个模块查看详情
                    import random
                    mod_name = modules[0].get("name", modules[0].get("id", ""))
                    if mod_name:
                        self.client.get(
                            f"/api/modules/{mod_name}",
                            headers=self.headers,
                            name="/api/modules/[name]",
                        )

    @task(2)
    def root_endpoint(self):
        """根端点健康检查。"""
        with self.client.get("/", name="/") as resp:
            if resp.status_code != 200:
                resp.failure(f"Root returned {resp.status_code}")

    @task(2)
    def prometheus_metrics(self):
        """Prometheus 指标端点。"""
        with self.client.get("/metrics", name="/metrics") as resp:
            if resp.status_code != 200:
                resp.failure(f"Metrics returned {resp.status_code}")

    @task(1)
    def scheduler_status(self):
        """调度器状态。"""
        with self.client.get("/api/scheduler", headers=self.headers, name="/api/scheduler") as resp:
            if resp.status_code not in (200, 404):
                resp.failure(f"Scheduler returned {resp.status_code}")

    @task(1)
    def coordinator_status(self):
        """协调器状态。"""
        with self.client.get("/api/coordinator/status", headers=self.headers, name="/api/coordinator/status") as resp:
            if resp.status_code not in (200, 404):
                resp.failure(f"Coordinator returned {resp.status_code}")

    @task(1)
    def auth_config(self):
        """认证配置。"""
        with self.client.get("/api/auth/config", name="/api/auth/config") as resp:
            if resp.status_code != 200:
                resp.failure(f"Auth config returned {resp.status_code}")

    @task(1)
    def all_module_health(self):
        """查看模块健康状态（重型端点）。"""
        with self.client.get("/api/modules/health", headers=self.headers, name="/api/modules/health") as resp:
            if resp.status_code != 200:
                resp.failure(f"Health returned {resp.status_code}")
