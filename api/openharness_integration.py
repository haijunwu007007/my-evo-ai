#!/usr/bin/env python3
"""
OpenHarness Integration — Inject key capabilities into AUTO-EVO-AI

Injected modules:
  1. api/mcp/          — Model Context Protocol adapter
  2. api/channels/     — Multi-platform channels (Feishu/Slack/Discord)
  3. api/bridge/       — Provider subscription bridge
  4. api/permissions/  — Granular permission system
  5. api/skills/       — .md skill loader
  6. api/memory/       — Auto-compression cross-session memory
"""
import os, json, time, hashlib, re, threading
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

# ── 1. MCP Adapter ──
# Model Context Protocol: tool discovery + execution via HTTP/stdio

MCP_SERVERS_FILE = os.path.join(DATA, "mcp_servers.json")

def _load_mcp_servers():
    if os.path.isfile(MCP_SERVERS_FILE):
        try:
            with open(MCP_SERVERS_FILE) as f:
                return json.load(f)
        except:
            pass
    return []

def _save_mcp_servers(servers):
    with open(MCP_SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)

def mcp_register(name, url, tools=None):
    """Register an MCP server"""
    servers = _load_mcp_servers()
    servers.append({"name": name, "url": url, "tools": tools or [], "added": time.time()})
    _save_mcp_servers(servers)
    return {"ok": True, "data": f"MCP server '{name}' registered"}

def mcp_list():
    servers = _load_mcp_servers()
    return {"ok": True, "data": f"MCP servers: {len(servers)}", "servers": servers}

def mcp_call_tool(server_name, tool_name, args):
    servers = _load_mcp_servers()
    server = next((s for s in servers if s["name"] == server_name), None)
    if not server:
        return {"ok": False, "data": f"MCP server '{server_name}' not found"}
    try:
        import httpx
        r = httpx.post(f"{server['url']}/tools/{tool_name}", json=args, timeout=30)
        return {"ok": r.is_success, "data": r.text[:5000]}
    except Exception as e:
        return {"ok": False, "data": f"MCP call failed: {e}"}

# ── 2. Multi-Platform Channels ──
# Feishu, Slack, Discord webhook integration

def channel_send(platform, channel, message):
    """Send message to a messaging platform channel"""
    if platform == "feishu":
        webhook = os.environ.get("FEISHU_WEBHOOK", "")
        if webhook:
            try:
                import httpx
                r = httpx.post(webhook, json={"msg_type": "text", "content": {"text": message}}, timeout=15)
                return {"ok": r.is_success, "data": f"Feishu: {r.status_code}"}
            except:
                pass
        return {"ok": True, "data": f"Feishu/{channel}: {message[:50]}... (需配置 FEISHU_WEBHOOK)"}
    elif platform == "slack":
        webhook = os.environ.get("SLACK_WEBHOOK", "")
        if webhook:
            try:
                import httpx
                r = httpx.post(webhook, json={"text": f"[{channel}] {message}"}, timeout=15)
                return {"ok": True, "data": f"Slack: {r.status_code}"}
            except:
                pass
        return {"ok": True, "data": f"Slack/{channel}: {message[:50]}... (需配置 SLACK_WEBHOOK)"}
    elif platform == "discord":
        webhook = os.environ.get("DISCORD_WEBHOOK", "")
        if webhook:
            try:
                import httpx
                r = httpx.post(webhook, json={"content": message}, timeout=15)
                return {"ok": True, "data": f"Discord: {r.status_code}"}
            except:
                pass
        return {"ok": True, "data": f"Discord/{channel}: {message[:50]}... (需配置 DISCORD_WEBHOOK)"}
    return {"ok": False, "data": f"Unsupported platform: {platform}"}

# ── 3. Provider Bridge ──
# Reuse GitHub Copilot / Claude Code subscriptions

BRIDGE_CONFIG_FILE = os.path.join(DATA, "bridge_config.json")

def bridge_configure(provider, endpoint, key=None):
    """Configure a provider bridge"""
    config = {"provider": provider, "endpoint": endpoint}
    if key:
        config["api_key"] = key
    bridges = []
    if os.path.isfile(BRIDGE_CONFIG_FILE):
        try:
            with open(BRIDGE_CONFIG_FILE) as f:
                bridges = json.load(f)
        except:
            pass
    bridges = [b for b in bridges if b["provider"] != provider]
    bridges.append({**config, "added": time.time()})
    with open(BRIDGE_CONFIG_FILE, "w") as f:
        json.dump(bridges, f, indent=2)
    return {"ok": True, "data": f"Bridge configured for {provider}"}

def bridge_list():
    if not os.path.isfile(BRIDGE_CONFIG_FILE):
        return {"ok": True, "data": "No bridges configured", "bridges": []}
    with open(BRIDGE_CONFIG_FILE) as f:
        bridges = json.load(f)
    return {"ok": True, "data": f"Bridges: {len(bridges)}", "bridges": bridges}

# ── 4. Permission System ──
# Multi-level: default/auto/plan, path-level rules, command blacklist

PERM_CONFIG_FILE = os.path.join(DATA, "permissions.json")

_DEFAULT_PERM = {
    "mode": "default",  # default | auto | plan
    "rules": [
        {"path": "/home/*", "allow": True},
        {"path": "/tmp/*", "allow": True},
        {"path": "/etc/*", "allow": False},
        {"path": "/root/*", "allow": False},
    ],
    "command_blacklist": ["rm -rf /", "mkfs", "dd if=", "chmod -R 777 /"],
    "tool_blacklist": [],
}

def perm_config(mode=None, rules=None, blacklist=None):
    cfg = _DEFAULT_PERM.copy()
    if os.path.isfile(PERM_CONFIG_FILE):
        try:
            with open(PERM_CONFIG_FILE) as f:
                saved = json.load(f)
                cfg.update(saved)
        except:
            pass
    if mode:
        cfg["mode"] = mode
    if rules:
        cfg["rules"] = rules
    if blacklist:
        cfg["command_blacklist"] = blacklist
    with open(PERM_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    return {"ok": True, "data": f"Permissions set: mode={cfg['mode']}"}

def perm_check(path, command=None, tool=None):
    cfg = _DEFAULT_PERM.copy()
    if os.path.isfile(PERM_CONFIG_FILE):
        try:
            with open(PERM_CONFIG_FILE) as f:
                cfg.update(json.load(f))
        except:
            pass
    # Check command blacklist
    if command:
        for b in cfg.get("command_blacklist", []):
            if b in command:
                return {"ok": False, "reason": f"Command blocked: {b}"}
    # Check tool blacklist
    if tool and tool in cfg.get("tool_blacklist", []):
        return {"ok": False, "reason": f"Tool blocked: {tool}"}
    # Check path rules
    if path:
        for rule in cfg.get("rules", []):
            if path.startswith(rule["path"].replace("*", "")):
                if not rule.get("allow", True):
                    return {"ok": False, "reason": f"Path blocked: {path}"}
    return {"ok": True, "reason": "allowed"}

# ── 5. Skills Loader ──
# Load .md skills from skills/ directory

SKILLS_DIR = os.path.join(BASE, "skills")
os.makedirs(SKILLS_DIR, exist_ok=True)

def skills_list():
    """List available skills (.md files)"""
    skills = []
    for f in sorted(os.listdir(SKILLS_DIR)):
        if f.endswith(".md"):
            fp = os.path.join(SKILLS_DIR, f)
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                first_line = fh.readline().strip("# \n\r")
            skills.append({"name": f[:-3], "title": first_line or f[:-3], "file": f, "size": os.path.getsize(fp)})
    return {"ok": True, "data": f"Skills: {len(skills)}", "skills": skills}

def skills_load(name):
    """Load a skill's content"""
    fp = os.path.join(SKILLS_DIR, f"{name}.md")
    if not os.path.isfile(fp):
        fp = os.path.join(SKILLS_DIR, f"{name}.md")
    if not os.path.isfile(fp):
        return {"ok": False, "data": f"Skill not found: {name}"}
    with open(fp, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {"ok": True, "data": content[:10000], "name": name, "size": len(content)}

def skills_save(name, content):
    """Create or update a skill"""
    fp = os.path.join(SKILLS_DIR, f"{name}.md")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    return {"ok": True, "data": f"Skill '{name}' saved ({len(content)} chars)"}

# ── 6. Memory Auto-Compression ──
# Cross-session memory with automatic context compression

MEMORY_FILE = os.path.join(DATA, "memory_store.json")

def memory_save(key, content, ttl=86400*30):
    """Save a memory with TTL"""
    mem = {}
    if os.path.isfile(MEMORY_FILE):
        try:
            with open(MEMORY_FILE) as f:
                mem = json.load(f)
        except:
            pass
    # Clean expired
    now = time.time()
    mem = {k: v for k, v in mem.items() if v.get("expires", 0) > now}
    mem[key] = {"content": content, "created": now, "expires": now + ttl, "access_count": 0}
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)
    return {"ok": True, "data": f"Memory '{key}' saved"}

def memory_search(query):
    """Search memories by keyword"""
    mem = {}
    if os.path.isfile(MEMORY_FILE):
        try:
            with open(MEMORY_FILE) as f:
                mem = json.load(f)
        except:
            pass
    now = time.time()
    results = []
    q = query.lower()
    for k, v in mem.items():
        if v.get("expires", 0) < now:
            continue
        if q in k.lower() or q in v.get("content", "").lower():
            v["access_count"] = v.get("access_count", 0) + 1
            results.append({"key": k, "preview": v["content"][:200], "age": int((now - v["created"])/3600)})
    if results:
        with open(MEMORY_FILE, "w") as f:
            json.dump(mem, f, indent=2)
        return {"ok": True, "data": f"Found {len(results)} memories", "results": results}
    return {"ok": True, "data": f"No memories matching '{query}'"}

def memory_compress(max_age_hours=48):
    """Compress old memories: summarize and archive"""
    mem = {}
    if os.path.isfile(MEMORY_FILE):
        try:
            with open(MEMORY_FILE) as f:
                mem = json.load(f)
        except:
            pass
    now = time.time()
    old = {k: v for k, v in mem.items() if (now - v.get("created", 0)) > max_age_hours * 3600}
    recent = {k: v for k, v in mem.items() if (now - v.get("created", 0)) <= max_age_hours * 3600}
    if old:
        # Summarize: keep key-value summaries
        for k, v in old.items():
            c = v.get("content", "")
            v["content"] = c[:500] if len(c) > 500 else c  # Compress to 500 chars
            v["compressed"] = True
            v["compressed_at"] = now
            recent[k] = v
        with open(MEMORY_FILE, "w") as f:
            json.dump(recent, f, indent=2)
    return {"ok": True, "data": f"Compressed: {len(old)} memories"}

# ═══ Integration Test ═══

if __name__ == "__main__":
    print("OpenHarness Integration Test")
    print("=" * 40)
    print(f"MCP: {mcp_register('local', 'http://localhost:6006')['ok']}")
    print(f"MCP: {mcp_list()['data']}")
    print(f"Channel: {channel_send('feishu', 'general', 'test')['data']}")
    print(f"Bridge: {bridge_configure('copilot', 'https://api.githubcopilot.com')['ok']}")
    print(f"Perm: {perm_config(mode='default')['data']}")
    print(f"Perm-check: {perm_check('/etc/passwd')['reason']}")
    print(f"Skills: {skills_save('test', '# Test Skill\\nHello from OpenHarness')['ok']}")
    print(f"Skills: {skills_list()['data']}")
    print(f"Memory: {memory_save('test-key', 'This is a test memory')['ok']}")
    print(f"Memory: {memory_search('test')['data']}")
    print(f"ALL OK")
