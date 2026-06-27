"""Docker 部署技能 — subprocess"""
import subprocess, json

skill_def = {
    "name": "docker-deploy", "version": "1.0.0",
    "description": "Docker Compose 容器部署",
    "author": "AUTO-EVO-AI", "category": "系统", "icon": "🐳",
    "tags": ["Docker", "容器", "部署"],
    "input_schema": {"type": "object", "properties": {"service": {"type": "string", "enum": ["portainer", "gitea", "metabase", "nocodb", "dify", "jellyfin"]}}},
    "output_schema": {"type": "object", "properties": {"status": {"type": "string"}, "container_id": {"type": "string"}}}
}

def execute(params, context=None):
    service = params.get("service", "")
    if not service:
        return {"status": "error", "container_id": "", "error": "请提供服务名称"}
    try:
        r = subprocess.run(["docker", "ps", "-a", "--filter", f"name={service}", "--format", "{{.ID}} {{.Status}}"],
                           capture_output=True, text=True, timeout=15)
        lines = [l for l in r.stdout.strip().split("\n") if l]
        if lines:
            parts = lines[0].split(None, 1)
            return {"status": parts[1] if len(parts) > 1 else "running", "container_id": parts[0]}
        # 尝试启动
        r2 = subprocess.run(["docker", "run", "-d", "--name", service, service], capture_output=True, text=True, timeout=30)
        if r2.returncode == 0:
            return {"status": "created", "container_id": r2.stdout.strip()}
        return {"status": "error", "container_id": "", "error": r2.stderr.strip()[:200]}
    except FileNotFoundError:
        return {"status": "error", "container_id": "", "error": "Docker 未安装或不在 PATH 中"}
    except Exception as e:
        return {"status": "error", "container_id": "", "error": str(e)[:200]}
