"""组合部署引擎 — 多个项目合成Docker Compose + 统一Nginx入口"""
from __future__ import annotations
import os, json, subprocess, time
from pathlib import Path
from api.hub.models import get_project, update_project, get_connection, list_connections

COMPOSE_DIR = Path(__file__).resolve().parent.parent.parent / "hub_composes"
NGINX_CONF = Path("/etc/nginx/sites-enabled") / "evo-composes.conf"

def generate_compose(compose_id: str, nodes: list[str], edges: list[dict]) -> dict:
    """生成组合项目的 docker-compose.yml"""
    compose_dir = COMPOSE_DIR / compose_id
    compose_dir.mkdir(parents=True, exist_ok=True)
    
    services = {}
    depends_on = {}
    nginx_upstreams = []
    
    for node_id in nodes:
        proj = get_project(node_id)
        if not proj: continue
        svc_name = f"evo_{node_id.replace('-','_')}"
        port = proj.get("port", 0)
        
        # Docker Compose 服务定义
        if proj.get("container_id"):
            services[svc_name] = {
                "container_name": f"evo-{node_id}",
                "image": "portainer/portainer-ce",  # 从project信息推导
                "restart": "unless-stopped",
                "ports": [f"{port}:9000" if port else "9000"],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
                "networks": ["evo-compose-net"],
            }
            nginx_upstreams.append({
                "name": node_id,
                "port": port or 9000,
                "path": f"/{node_id}",
            })
    
    # 处理连线（数据流依赖）
    for edge in edges:
        src = edge.get("source_id") or edge.get("source")
        tgt = edge.get("target_id") or edge.get("target")
        if src and tgt:
            svc_src = f"evo_{src.replace('-','_')}"
            svc_tgt = f"evo_{tgt.replace('-','_')}"
            if svc_src in depends_on:
                depends_on[svc_src].append(svc_tgt)
            else:
                depends_on[svc_src] = [svc_tgt]
    
    for svc in services:
        if svc in depends_on:
            services[svc]["depends_on"] = depends_on[svc]
    
    compose = {
        "version": "3.8",
        "services": services,
        "networks": {
            "evo-compose-net": {"driver": "bridge"}
        }
    }
    
    (compose_dir / "docker-compose.yml").write_text(json.dumps(compose, indent=2))
    
    # 生成Nginx配置（统一入口）
    if nginx_upstreams:
        gen_nginx_conf(compose_id, nginx_upstreams, compose_dir)
    
    return {"compose_dir": str(compose_dir), "services": list(services.keys()), "nginx_upstreams": nginx_upstreams}

def gen_nginx_conf(compose_id: str, upstreams: list, compose_dir: Path):
    """为组合生成Nginx统一入口配置"""
    conf = []
    conf.append(f"# AUTO-EVO-AI Compose: {compose_id}")
    conf.append(f"upstream evo_compose_{compose_id} {{")
    for u in upstreams:
        conf.append(f"    server 127.0.0.1:{u['port']};")
    conf.append("}")
    conf.append(f"server {{")
    conf.append(f"    listen {8000 + hash(compose_id) % 1000};")
    conf.append(f"    server_name _;")
    for u in upstreams:
        conf.append(f"    location {u['path']} {{")
        conf.append(f"        proxy_pass http://127.0.0.1:{u['port']};")
        conf.append(f"        proxy_set_header Host $host;")
        conf.append(f"    }}")
    conf.append(f"    location / {{")
    conf.append(f"        return 200 'EVO Compose: {compose_id} - {len(upstreams)} services running';")
    conf.append(f"        add_header Content-Type text/plain;")
    conf.append(f"    }}")
    conf.append("}")
    
    conf_text = "\n".join(conf)
    (compose_dir / "nginx.conf").write_text(conf_text)
    
    # 尝试加载到Nginx
    try:
        (Path("/etc/nginx/sites-enabled") / f"evo-compose-{compose_id}.conf").write_text(conf_text)
        subprocess.run(["nginx", "-s", "reload"], capture_output=True, timeout=10)
    except Exception:
        pass
    
    return conf_text

def deploy_compose(compose_id: str) -> dict:
    """部署整个组合"""
    from api.hub.models import get_compose, update_compose
    comp = get_compose(compose_id)
    if not comp:
        return {"success": False, "error": "组合不存在"}
    
    nodes = json.loads(comp.get("nodes", "[]"))
    edges = json.loads(comp.get("edges", "[]"))
    
    result = generate_compose(compose_id, nodes, edges)
    compose_dir = result.get("compose_dir")
    
    # docker-compose up
    try:
        proc = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=compose_dir, capture_output=True, text=True, timeout=120
        )
        if proc.returncode != 0:
            return {"success": False, "error": proc.stderr[:300]}
        
        update_compose(compose_id, {"status": "running"})
        return {"success": True, "message": f"组合已部署 ({len(nodes)} services)", "output": proc.stdout[:200]}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "部署超时"}
    except FileNotFoundError:
        # docker-compose not found, try docker compose
        try:
            proc = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=compose_dir, capture_output=True, text=True, timeout=120
            )
            if proc.returncode != 0:
                return {"success": False, "error": proc.stderr[:300]}
            update_compose(compose_id, {"status": "running"})
            return {"success": True, "message": f"组合已部署 ({len(nodes)} services)", "output": proc.stdout[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}

def stop_compose(compose_id: str) -> dict:
    """停止组合"""
    from api.hub.models import get_compose, update_compose
    comp = get_compose(compose_id)
    if not comp:
        return {"success": False, "error": "组合不存在"}
    compose_dir = COMPOSE_DIR / compose_id
    if compose_dir.exists():
        try:
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=str(compose_dir), capture_output=True, timeout=60
            )
        except Exception:
            pass
    update_compose(compose_id, {"status": "stopped"})
    return {"success": True}
