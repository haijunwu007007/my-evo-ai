import os

files = [
    "postgres_db.py",
    "mongodb_nosql.py",
    "redis_cache.py",
    "elasticsearch_search.py",
    "object_storage.py",
    "page_cache.py",
    "system_monitor.py",
    "log_collector.py",
    "alert_manager.py",
    "config_center.py",
    "data_pipeline.py",
    "task_queue.py",
    "message_queue.py",
    "jwt_token.py",
    "data_encrypt.py",
    "firewall_rules.py",
    "oauth_provider.py",
    "oauth_server.py",
    "permission_rbac.py",
]
for f in files:
    c = open(f, encoding="utf-8", errors="ignore").read()
    has_under = "self._config" in c
    has_dot = "self.config" in c
    has_mc = "module_class" in c
    lines = c.count("\n")
    logger.info(f"{f}: lines={lines}, self._config={has_under}, self.config={has_dot}, module_class={has_mc}"))
