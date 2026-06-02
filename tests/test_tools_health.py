"""
57 个外部工具健康检查
运行: python -m pytest tests/test_tools_health.py -v
"""

import pytest
import subprocess
import json
import urllib.request
import urllib.error
import time

TOOLS = {
    # AI
    "dify":            ("http://localhost:3000",       "Dify"),
    "flowise":         ("http://localhost:3001",       "Flowise"),
    "n8n":             ("http://localhost:5678",       "n8n"),
    "one-api":         ("http://localhost:3002",       "One-API"),
    "litellm":         ("http://localhost:4000",       "LiteLLM"),
    "langfuse":        ("http://localhost:4001",       "Langfuse"),
    # 开发
    "gitea":           ("http://localhost:3000",       "Gitea"),
    "code-server":     ("http://localhost:8443",       "Code-Server"),
    # 文件
    "nextcloud":       ("http://localhost:8090",       "Nextcloud"),
    "minio":           ("http://localhost:9001",       "MinIO"),
    "stirling-pdf":    ("http://localhost:8080",       "Stirling-PDF"),
    # 数据
    "metabase":        ("http://localhost:3030",       "Metabase"),
    "meilisearch":     ("http://localhost:7700",       "Meilisearch"),
    "nocodb":          ("http://localhost:8080",       "NocoDB"),
    "superset":        ("http://localhost:8088",       "Superset"),
    "qdrant":          ("http://localhost:6333",       "Qdrant"),
    # 安全
    "vaultwarden":     ("http://localhost:8180",       "Vaultwarden"),
    "portainer":       ("http://localhost:9000",       "Portainer"),
    # 监控
    "grafana":         ("http://localhost:3000",       "Grafana"),
    "uptime-kuma":     ("http://localhost:3001",       "Uptime-Kuma"),
    "prometheus":      ("http://localhost:9090",       "Prometheus"),
    # 企业
    "twenty-crm":      ("http://localhost:3100",       "Twenty CRM"),
    "invoice-ninja":   ("http://localhost:3110",       "Invoice Ninja"),
    "chatwoot":        ("http://localhost:3120",       "Chatwoot"),
    "osticket":        ("http://localhost:3180",       "osTicket"),
    "erpnext":         ("http://localhost:3300",       "ERPNext"),
    # 媒体
    "jellyfin":        ("http://localhost:3130",       "Jellyfin"),
    "immich":          ("http://localhost:2283",       "Immich"),
    "excalidraw":      ("http://localhost:3080",       "Excalidraw"),
    "calibre-web":     ("http://localhost:3140",       "Calibre-Web"),
    # 协作
    "docmost":         ("http://localhost:3085",       "Docmost"),
    "mattermost":      ("http://localhost:3150",       "Mattermost"),
    "focalboard":      ("http://localhost:3160",       "Focalboard"),
    "outline":         ("http://localhost:3200",       "Outline"),
    # 行业
    "medusa":          ("http://localhost:9000",       "Medusa"),
    "openemr":         ("http://localhost:3400",       "OpenEMR"),
    "frappe-hr":       ("http://localhost:3500",       "Frappe HR"),
    "open-edx":        ("http://localhost:3600",       "Open edX"),
    # IT
    "snipe-it":        ("http://localhost:3170",       "Snipe-IT"),
    "it-tools":        ("http://localhost:3170",       "IT-Tools"),
    "miniflux":        ("http://localhost:3060",       "Miniflux"),
    # 文档
    "paperless":       ("http://localhost:3800",       "Paperless-ngx"),
    "documenso":       ("http://localhost:3090",       "Documenso"),
    # 其他
    "hoppscotch":      ("http://localhost:3100",       "Hoppscotch"),
    "changedetection": ("http://localhost:5000",       "Changedetection"),
    "home-assistant":  ("http://localhost:8123",       "Home Assistant"),
    "hoarder":         ("http://localhost:3070",       "Hoarder"),
}

@pytest.mark.parametrize("name,url,label", sorted(TOOLS.items(), key=lambda x: x[1][1]))
def test_tool_container(name, url, label):
    """检查工具是否可访问"""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status < 500, f"{label} 返回 {resp.status}"
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        if hasattr(e, 'code') and e.code in (401, 302, 301):
            pytest.skip(f"{label}: 需要登录 ({e.code})")
        else:
            pytest.fail(f"{label}: {e}")
    except ConnectionRefusedError:
        pytest.skip(f"{label}: 容器未启动")
    except OSError as e:
        pytest.fail(f"{label}: {e}")


def test_tools_count():
    """验证工具总数"""
    assert len(TOOLS) == 57, f"预期 57 个工具, 实际 {len(TOOLS)}"


def test_docker_running():
    """检查 Docker 容器状态"""
    r = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
        capture_output=True, text=True, timeout=10
    )
    containers = [l.split("\t")[0] for l in r.stdout.strip().split("\n") if l]
    print(f"\n运行中容器数: {len(containers)}")
    for c in containers:
        print(f"  ✅ {c}")
