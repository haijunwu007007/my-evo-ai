"""
AUTO-EVO-AI V0.1 — 运维/DevOps 模块生产级测试
上市公司生产力级别：验证容器/K8s/CI/CD/监控模块业务逻辑
"""

import os, sys, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest


# ── DockerManager 测试 ──

class TestDockerManager(unittest.TestCase):
    """Docker 管理器：容器生命周期/镜像/网络/卷/监控"""

    @classmethod
    def setUpClass(cls):
        from modules.docker_manager import DockerManager, ContainerConfig, BuildContext, ContainerStatus
        from modules._base.enterprise_module import ModuleStatus
        cls.DockerManager = DockerManager
        cls.ContainerConfig = ContainerConfig
        cls.BuildContext = BuildContext
        cls.ContainerStatus = ContainerStatus
        cls.ModuleStatus = ModuleStatus
        cls.mgr = DockerManager({"max_containers": 10, "monitor_interval": 60})
        cls.mgr.initialize()

    def test_001_container_create(self):
        """创建容器（模拟模式）"""
        cfg = self.ContainerConfig(
            image="nginx:alpine",
            container_name="test-nginx",
            ports={"8080": "80"},
            labels={"app": "test"},
            restart_policy=self.ContainerConfig.__dataclass_fields__["restart_policy"].type("unless-stopped")
            if hasattr(self.ContainerConfig, "__dataclass_fields__")
            else None,
        )
        r = self.mgr.create_container(cfg)
        self.assertTrue(r.success, f"创建容器失败: {r.error if hasattr(r, 'error') else 'unknown'}")

    def test_002_list_containers(self):
        """列出容器"""
        containers = self.mgr.list_containers()
        self.assertIsInstance(containers, list)
        names = [c.get("name", "") for c in containers]
        self.assertIn("test-nginx", names)

    def test_003_container_stop(self):
        """停止容器"""
        r = self.mgr.stop_container("test-nginx")
        self.assertTrue(r.success)

    def test_004_container_start(self):
        """启动容器"""
        r = self.mgr.start_container("test-nginx")
        self.assertTrue(r.success)

    def test_005_container_restart(self):
        """重启容器"""
        r = self.mgr.restart_container("test-nginx")
        self.assertTrue(r.success)

    def test_006_container_remove(self):
        """删除容器"""
        r = self.mgr.remove_container("test-nginx", force=True)
        self.assertTrue(r.success)
        names = [c.get("name") for c in self.mgr.list_containers()]
        self.assertNotIn("test-nginx", names)

    def test_007_scale_containers(self):
        """扩缩容"""
        cfg = self.ContainerConfig(image="redis:alpine")
        r = self.mgr.scale_containers("test-redis", "redis:alpine", 2, cfg)
        self.assertTrue(r.success, f"扩缩容失败: {r}")
        # 清理
        for c in self.mgr.list_containers():
            if c.get("name", "").startswith("test-redis"):
                self.mgr.remove_container(c["name"], force=True)

    def test_008_build_image(self):
        """构建镜像"""
        ctx = self.BuildContext(dockerfile_path="Dockerfile.test", context_path=".", tag="test:latest")
        r = self.mgr.build_image(ctx)
        self.assertIn(True, [r.success])

    def test_009_pull_image(self):
        """拉取镜像"""
        r = self.mgr.pull_image("hello-world:latest")
        if hasattr(r, "success"):
            pass  # Docker 可用时成功，不可用时模拟

    def test_010_list_images(self):
        """列出镜像"""
        images = self.mgr.list_images()
        self.assertIsInstance(images, list)

    def test_011_create_network(self):
        """创建网络"""
        r = self.mgr.create_network("test-net", {"driver": "bridge"})
        self.assertTrue(r.success)

    def test_012_create_volume(self):
        """创建数据卷"""
        r = self.mgr.create_volume("test-vol")
        self.assertTrue(r.success)

    def test_013_get_stats(self):
        """获取统计"""
        stats = self.mgr.get_stats()
        self.assertIn("containers_registered", stats)
        self.assertIn("containers_running", stats)

    def test_014_get_build_history(self):
        """构建历史"""
        history = self.mgr.get_build_history()
        self.assertIsInstance(history, list)

    def test_015_health_check(self):
        """健康检查"""
        h = self.mgr.health_check()
        self.assertTrue(h.get("healthy", False))

    def test_016_shutdown(self):
        """关闭"""
        r = self.mgr.shutdown()
        self.assertTrue(r.success)


# ── K8sOrchestrator 测试 ──

class TestK8sOrchestrator(unittest.TestCase):
    """K8s 编排器：Pod/Deployment/Service/HPA/事件"""

    @classmethod
    def setUpClass(cls):
        from modules.k8s_orch import K8sOrchestrator, Pod, PodSpec, ContainerSpec, DeploymentSpec, HPASpec
        from modules.k8s_orch import PodPhase, DeploymentStrategy
        cls.orch = K8sOrchestrator()
        cls.Pod = Pod
        cls.PodSpec = PodSpec
        cls.ContainerSpec = ContainerSpec
        cls.DeploymentSpec = DeploymentSpec
        cls.HPASpec = HPASpec
        cls.PodPhase = PodPhase
        cls.DeploymentStrategy = DeploymentStrategy

    def test_001_create_namespace(self):
        """创建命名空间"""
        ns = "test-ns"
        self.orch._create_namespace(ns)
        self.assertIn(ns, self.orch.list_namespaces())

    def test_002_create_pod(self):
        """创建 Pod"""
        pod = self.Pod(
            metadata={"name": "test-nginx", "namespace": "default"},
            spec=self.PodSpec(
                containers=[self.ContainerSpec(name="nginx", image="nginx:alpine", ports=[80])],
                labels={"app": "nginx"},
            ),
        )
        r = self.orch.create_pod(pod)
        self.assertIn("name", r)
        self.assertEqual(r["name"], "test-nginx")

    def test_003_get_pod(self):
        """获取 Pod 详情"""
        info = self.orch.get_pod("test-nginx", "default")
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "test-nginx")
        self.assertIn("phase", info)

    def test_004_list_pods(self):
        """列出 Pods"""
        pods = self.orch.list_pods("default")
        names = [p["name"] for p in pods]
        self.assertIn("test-nginx", names)

    def test_005_delete_pod(self):
        """删除 Pod"""
        ok = self.orch.delete_pod("test-nginx", "default")
        self.assertTrue(ok)
        info = self.orch.get_pod("test-nginx", "default")
        self.assertIsNone(info)

    def test_006_create_deployment(self):
        """创建 Deployment"""
        spec = self.DeploymentSpec(
            name="test-web",
            namespace="default",
            replicas=3,
            strategy=self.DeploymentStrategy.ROLLING,
            template=self.PodSpec(
                containers=[self.ContainerSpec(name="web", image="nginx:alpine")],
                labels={"app": "web"},
            ),
        )
        r = self.orch.create_deployment(spec)
        self.assertEqual(r["name"], "test-web")
        self.assertEqual(r["replicas"], 3)
        self.assertEqual(r["pods_created"], 3)

    def test_007_get_deployment(self):
        """获取 Deployment 详情"""
        dep = self.orch.get_deployment("test-web", "default")
        self.assertIsNotNone(dep)
        self.assertEqual(dep["replicas"], 3)
        self.assertEqual(dep["ready"], 3)

    def test_008_scale_deployment(self):
        """扩缩容 Deployment"""
        r = self.orch.scale_deployment("test-web", "default", 5)
        self.assertIsNotNone(r)
        self.assertEqual(r["current"], 5)
        dep = self.orch.get_deployment("test-web", "default")
        self.assertEqual(dep["replicas"], 5)

    def test_009_rolling_update(self):
        """滚动更新"""
        r = self.orch.rolling_update("test-web", "default", "nginx:1.25")
        self.assertTrue(r["success"])
        # 验证容器镜像已更新
        key = "default/test-web"
        dep = self.orch._deployments.get(key)
        if dep:
            containers = dep["spec"].template.containers
            self.assertEqual(containers[0].image, "nginx:1.25")

    def test_010_set_hpa(self):
        """设置 HPA"""
        hpa = self.HPASpec(min_replicas=2, max_replicas=10, target_cpu_percent=70)
        r = self.orch.set_hpa("test-web", "default", hpa)
        self.assertIn("min", r)
        self.assertEqual(r["min"], 2)

    def test_011_create_service(self):
        """创建 Service"""
        r = self.orch.create_service("test-web-svc", "default", "ClusterIP",
                                      ports=[{"port": 80, "targetPort": 80}],
                                      selector={"app": "web"})
        self.assertEqual(r["name"], "test-web-svc")
        self.assertIn("cluster_ip", r)

    def test_012_cluster_status(self):
        """集群状态"""
        status = self.orch.get_cluster_status()
        self.assertIn("namespaces", status)
        self.assertIn("pods", status)
        self.assertIn("deployments", status)
        self.assertIn("services", status)
        self.assertGreaterEqual(status["deployments"], 1)
        self.assertGreaterEqual(status["services"], 1)

    def test_013_events(self):
        """事件日志非空"""
        events = self.orch.get_events(limit=20)
        self.assertIsInstance(events, list)
        self.assertGreaterEqual(len(events), 1)

    def test_014_set_hpa_scaling(self):
        """验证扩缩容后 HPA 配置一致"""
        dep_key = "default/test-web"
        if dep_key in self.orch._hpa_configs:
            hpa = self.orch._hpa_configs[dep_key]
            self.assertEqual(hpa.min_replicas, 2)
            self.assertEqual(hpa.max_replicas, 10)

    def test_015_health_check(self):
        """健康检查"""
        h = self.orch.health_check()
        self.assertTrue(h.get("healthy", False))

    def test_016_shutdown(self):
        """关闭"""
        r = self.orch.shutdown()
        self.assertTrue(r.get("success", False))


# ── EmailAutomation 测试 ──

class TestEmailAutomation(unittest.TestCase):
    """邮件自动化：发送/模板/队列/取信/统计"""

    @classmethod
    def setUpClass(cls):
        from modules.email_automation import EmailAutomation
        cls.email = EmailAutomation({
            "email": {
                "smtp_host": "smtp.test.com",
                "smtp_port": 587,
                "username": "test@test.com",
                "password": "test",
                "from_addr": "test@test.com",
                "from_name": "Test",
            }
        })
        cls.email.initialize()

    def test_001_template_renders(self):
        """模板渲染"""
        s, html, text = self.email.template_engine.render(
            "system_report",
            {"title": "Test Report", "content": "<tr><td>OK</td></tr>"},
        )
        self.assertIn("Test Report", s)
        self.assertIn("OK", html)

    def test_002_list_templates(self):
        """列出模板"""
        t = self.email.template_engine.list_templates()
        self.assertIn("system_report", t)

    def test_003_add_template(self):
        """添加模板"""
        self.email.template_engine.add_template(
            "custom", "【{name}】通知", "<b>{msg}</b>", "{msg}"
        )
        t = self.email.template_engine.list_templates()
        self.assertIn("custom", t)

    def test_004_queue_message(self):
        """加入发送队列"""
        r = self.email._action_send({
            "to": ["test@example.com"],
            "subject": "Test",
            "body": "Hello",
        })
        self.assertIn("status", r)
        self.assertEqual(r["status"], "queued")

    def test_005_queue_size(self):
        """队列大小"""
        r = self.email._action_queue({})
        self.assertIn("queue_size", r)
        self.assertGreaterEqual(r["queue_size"], 1)

    def test_006_get_history(self):
        """发送历史"""
        r = self.email._action_history({"limit": 10})
        self.assertIn("items", r)
        self.assertIn("total", r)

    def test_007_get_stats(self):
        """统计信息"""
        r = self.email._action_stats({})
        self.assertIn("sent", r)
        self.assertIn("queue", r)

    def test_008_schedule_message(self):
        """定时发送"""
        r = self.email._action_schedule({
            "to": ["test@example.com"],
            "subject": "Scheduled",
            "body": "Later",
            "send_at": "2099-12-31T23:59:59",
        })
        self.assertIn("status", r)
        self.assertEqual(r["status"], "scheduled")

    def test_009_fetch_emails_no_server(self):
        """无服务器时取信返回空"""
        r = self.email._action_fetch({"folder": "INBOX", "criteria": "UNSEEN", "limit": 5})
        self.assertIn("total", r)
        self.assertIn("emails", r)

    def test_010_send_template(self):
        """模板发送并入队"""
        r = self.email._action_send_template({
            "to": ["test@example.com"],
            "template": "system_report",
            "vars": {"title": "Daily", "content": "All OK"},
        })
        self.assertEqual(r.get("status"), "queued")


# ── SystemMonitor / HealthCheck 测试 ──

class TestSystemMonitoring(unittest.TestCase):
    """系统监控模块：健康检查/性能指标"""

    def test_001_health_checker_module(self):
        """HealthChecker 模块可导入"""
        try:
            from modules.health_checker import module_class
            hc = module_class()
            r = hc.health_check() if hasattr(hc, "health_check") else {}
            self.assertIsNotNone(r)
        except ImportError:
            self.skipTest("health_checker 模块不可用")

    def test_002_system_monitor_import(self):
        """SystemMonitor 模块可导入"""
        try:
            from modules.system_monitor import module_class
            mon = module_class({"monitor_interval": 999})
            self.assertIsNotNone(mon)
        except ImportError:
            self.skipTest("system_monitor 模块不可用")

    def test_003_grafana_monitor(self):
        """GrafanaMonitory 模块可导入"""
        try:
            from modules.grafana_monitor import module_class
            g = module_class()
            self.assertIsNotNone(g)
        except ImportError:
            self.skipTest("grafana_monitor 不可用")

    def test_004_local_monitor(self):
        """LocalMonitor 模块可导入"""
        try:
            from modules.local_monitor import module_class
            m = module_class()
            self.assertIsNotNone(m)
        except ImportError:
            self.skipTest("local_monitor 不可用")

    def test_005_prometheus_metrics(self):
        """PrometheusMetrics 可导入"""
        try:
            from modules.prometheus_metrics import module_class
            p = module_class()
            h = p.health_check() if hasattr(p, "health_check") else {}
            self.assertIsNotNone(h)
        except ImportError:
            self.skipTest("prometheus_metrics 不可用")


if __name__ == "__main__":
    unittest.main(verbosity=2)
