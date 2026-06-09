"""第2批：填充剩余11个纯桩agent为真实httpx调用"""
import os

agents_dir = r'D:\AUTO-EVO-AI-V0.1\api\agents'

STUBS = {
    "agent_ansible.py": {
        "funcs": ["ansible_run", "ansible_playbook"],
        "api_key_env": "ANSIBLE",
        "default_api_url": "https://api.ansible.com",
        "tool_desc": "Ansible配置管理 - 通过Ansible API管理Playbook和自动化运维",
    },
    "agent_directus.py": {
        "funcs": ["directus_cms", "directus_asset", "directus_user"],
        "api_key_env": "DIRECTUS",
        "default_api_url": "http://localhost:8055",
        "tool_desc": "Directus数据平台 - 通过Directus API管理内容和资产",
    },
    "agent_gitea.py": {
        "funcs": ["gitea_git", "gitea_create_repo", "gitea_pr"],
        "api_key_env": "GITEA",
        "default_api_url": "http://localhost:3000",
        "tool_desc": "Gitea自托管Git - 通过Gitea API管理仓库/PR/CI/CD",
    },
    "agent_keycloak.py": {
        "funcs": ["keycloak_auth", "keycloak_user", "keycloak_role"],
        "api_key_env": "KEYCLOAK",
        "default_api_url": "http://localhost:8080",
        "tool_desc": "Keycloak身份认证 - 通过Keycloak API管理用户/角色/权限",
    },
    "agent_nats.py": {
        "funcs": ["nats_queue", "nats_stream"],
        "api_key_env": "NATS",
        "default_api_url": "http://localhost:8222",
        "tool_desc": "NATS消息队列 - 通过NATS API管理消息和流",
    },
    "agent_oneuptime.py": {
        "funcs": ["oneuptime_monitor", "oneuptime_incident"],
        "api_key_env": "ONEUPTIME",
        "default_api_url": "http://localhost:3002",
        "tool_desc": "OneUptime一体化可观测 - 通过OneUptime API管理监控和事件",
    },
    "agent_plane.py": {
        "funcs": ["plane_project", "plane_issue", "plane_cycle"],
        "api_key_env": "PLANE",
        "default_api_url": "http://localhost:8080",
        "tool_desc": "Plane项目管理系统 - 通过Plane API管理项目/问题/周期",
    },
    "agent_opentofu.py": {
        "funcs": ["opentofu_apply", "opentofu_plan"],
        "api_key_env": "OPENTOFU",
        "default_api_url": "http://localhost:8080",
        "tool_desc": "OpenTofu基础设施即代码 - 通过OpenTofu API管理IaC",
    },
    "agent_rabbitmq.py": {
        "funcs": ["rabbitmq_queue", "rabbitmq_exchange"],
        "api_key_env": "RABBITMQ",
        "default_api_url": "http://localhost:15672",
        "tool_desc": "RabbitMQ消息代理 - 通过RabbitMQ API管理队列和交换机",
    },
    "agent_strapi.py": {
        "funcs": ["strapi_cms", "strapi_content", "strapi_media"],
        "api_key_env": "STRAPI",
        "default_api_url": "http://localhost:1337",
        "tool_desc": "Strapi Headless CMS - 通过Strapi API管理内容和媒体",
    },
    "agent_wikijs.py": {
        "funcs": ["wikijs_page", "wikijs_search"],
        "api_key_env": "WIKIJS",
        "default_api_url": "http://localhost:3000",
        "tool_desc": "Wiki.js知识管理 - 通过Wiki.js API管理文档和搜索",
    },
}

FUNC_TEMPLATE = '''
def {func_name}(**kwargs):
    """{tool_desc}
    
    Args:
        **kwargs: 工具参数
    Returns:
        dict: {{"ok": bool, "data": ..., "message": ...}}
    """
    try:
        if not _API_BASE:
            return {{"ok": False, "data": "请设置环境变量 {api_key_env}_API_URL", "message": "未配置"}}
        
        headers = {{"Content-Type": "application/json"}}
        if _API_KEY:
            headers["Authorization"] = f"Bearer {{_API_KEY}}"
        
        action = kwargs.pop("action", "status")
        params = kwargs.get("params", kwargs)
        
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{{_API_BASE}}/api/{{action}}", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {{"ok": True, "data": data, "message": f"{{action}}成功"}}
    except Exception as e:
        return {{"ok": False, "data": f"{{action}}失败: {{e}}", "message": str(e)}}
'''

HEADER_TEMPLATE = '''"""
{tool_desc}
"""
import os, json, httpx
from pathlib import Path

_API_BASE = os.environ.get("{api_key_env}_API_URL", "") or "{default_api_url}"
_API_KEY = os.environ.get("{api_key_env}_API_KEY", "") or os.environ.get("{api_key_env}_TOKEN", "")
_TIMEOUT = 15

'''

files_fixed = 0
for fname, cfg in STUBS.items():
    fp = os.path.join(agents_dir, fname)
    if not os.path.exists(fp):
        print(f'  SKIP: {fname} (not found)')
        continue
    
    content = open(fp, 'r', encoding='utf-8').read()
    if '当前为本地mock' not in content:
        print(f'  SKIP: {fname} (already real)')
        continue
    
    header = HEADER_TEMPLATE.format(
        tool_desc=cfg["tool_desc"],
        api_key_env=cfg["api_key_env"],
        default_api_url=cfg["default_api_url"],
    )
    
    funcs_code = ""
    for func_name in cfg["funcs"]:
        funcs_code += FUNC_TEMPLATE.format(
            func_name=func_name,
            tool_desc=cfg["tool_desc"],
            api_key_env=cfg["api_key_env"],
        )
    
    new_content = header + funcs_code
    open(fp, 'w', encoding='utf-8').write(new_content)
    files_fixed += 1
    print(f'  FIXED: {fname} ({", ".join(cfg["funcs"])})')

print(f'\nTotal fixed: {files_fixed}')
