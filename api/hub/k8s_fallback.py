"""K8s部署+自动降级到docker-compose"""
import logging
logger = logging.getLogger("evo.k8s_fallback")

import os, subprocess, json, yaml, tempfile

def check_k8s():
    """检查k8s是否可用"""
    try:
        r = subprocess.run(["kubectl", "cluster-info", "--request-timeout", "5s"],
                         capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return {"available": True, "version": r.stdout[:100]}
        return {"available": False, "reason": r.stderr.strip()[:100]}
    except FileNotFoundError:
        return {"available": False, "reason": "kubectl命令不存在"}
    except Exception as e:
        return {"available": False, "reason": str(e)[:100]}

def k8s_to_compose(k8s_yaml):
    """将简单的K8s Deployment转换为docker-compose格式"""
    import yaml
    try:
        docs = list(yaml.safe_load_all(k8s_yaml))
    except:
        return None
    services = {}
    for doc in docs:
        if doc is None: continue
        kind = doc.get("kind", "")
        name = doc.get("metadata", {}).get("name", "app")
        if kind in ("Deployment", "StatefulSet", "DaemonSet"):
            template = doc.get("spec", {}).get("template", {})
            container = (template.get("spec", {}).get("containers", []) or [{}])[0]
            image = container.get("image", "nginx")
            ports = []
            for p in container.get("ports", []):
                cp = p.get("containerPort", 80)
                ports.append(f"{cp}:{cp}")
            env = {}
            for e in container.get("env", []):
                if "value" in e:
                    env[e["name"]] = e["value"]
            service_def = {"image": image, "restart": "unless-stopped"}
            if ports: service_def["ports"] = ports
            if env: service_def["environment"] = env
            services[name] = service_def
        elif kind == "Service":
            svc_name = doc.get("metadata", {}).get("name", name)
            ports = []
            for p in doc.get("spec", {}).get("ports", []):
                ports.append(f"{p.get('port',80)}:{p.get('targetPort',80)}")
            if svc_name in services and ports:
                services[svc_name]["ports"] = ports
    if not services:
        return None
    compose = {"version": "3", "services": services}
    return yaml.dump(compose, default_flow_style=False)

def deploy_k8s_or_fallback(k8s_yaml, project_name="evo-k8s-app"):
    """部署K8s，不可用时降级到docker-compose"""
    k8s_ok = check_k8s()
    if k8s_ok["available"]:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(k8s_yaml)
                f.flush()
            r = subprocess.run(["kubectl", "apply", "-f", f.name],
                             capture_output=True, text=True, timeout=60)
            os.unlink(f.name)
            if r.returncode == 0:
                return {"ok": True, "data": f"K8s部署成功: {r.stdout[:200]}", "mode": "k8s"}
            return {"ok": False, "data": f"K8s失败: {r.stderr[:200]}", "mode": "k8s"}
        except Exception as e:
            return {"ok": False, "data": f"K8s异常: {e}", "mode": "k8s"}
    # 降级到docker-compose
    compose_yaml = k8s_to_compose(k8s_yaml)
    if not compose_yaml:
        return {"ok": False, "data": "K8s不可用且无法转换为compose配置", "mode": "fallback"}
    proj_dir = os.path.join("/tmp", project_name)
    os.makedirs(proj_dir, exist_ok=True)
    with open(os.path.join(proj_dir, "docker-compose.yml"), "w") as f:
        f.write(compose_yaml)
    try:
        r = subprocess.run(["docker-compose", "-f", os.path.join(proj_dir, "docker-compose.yml"), "up", "-d"],
                         capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return {"ok": True, "data": f"已降级到docker-compose部署: {proj_dir}", "mode": "docker-compose"}
        return {"ok": False, "data": f"docker-compose失败: {r.stderr[:200]}", "mode": "fallback"}
    except Exception as e:
        return {"ok": False, "data": f"降级失败: {e}", "mode": "fallback"}

def check_k8s_pods():
    """检查K8s pod状态"""
    try:
        r = subprocess.run(["kubectl", "get", "pods", "--all-namespaces"],
                         capture_output=True, text=True, timeout=15)
        return {"ok": True, "data": r.stdout[:1000]}
    except:
        return {"ok": False, "data": "K8s不可用"}
