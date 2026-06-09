"""Restructure api/ directory:
- routes_*.py → api/routes/
- agent_*.py (tools) → api/agents/  
- Update all import paths
"""
import os, re, sys

API = r"D:\AUTO-EVO-AI-V0.1\api"
files = [f for f in os.listdir(API) if f.endswith('.py') and f != '__init__.py']

# Categorize
routes = sorted([f for f in files if f.startswith('routes_')])
agents = sorted([f for f in files if f.startswith('agent_') and f not in ('agent_core.py','agent_llm.py','agent_tools.py','agent_concurrent.py')])
stay = [f for f in files if f not in routes and f not in agents] + ['agent_core.py','agent_llm.py','agent_tools.py','agent_concurrent.py']
stay = sorted(set(stay))

print(f"Routes: {len(routes)} → api/routes/")
print(f"Agents: {len(agents)} → api/agents/")
print(f"Stay: {len(stay)} (core files)")

# Create dirs
os.makedirs(os.path.join(API, 'routes'), exist_ok=True)
os.makedirs(os.path.join(API, 'agents'), exist_ok=True)

# Write __init__.py
for d in ['routes', 'agents']:
    init_path = os.path.join(API, d, '__init__.py')
    with open(init_path, 'w') as f:
        f.write(f'# {d} package\n')

# Move files
def move(src_path, dst_dir):
    dst_path = os.path.join(dst_dir, os.path.basename(src_path))
    os.rename(src_path, dst_path)
    return dst_path

for f in routes:
    move(os.path.join(API, f), os.path.join(API, 'routes'))
for f in agents:
    move(os.path.join(API, f), os.path.join(API, 'agents'))

print("\nFiles moved.")

# ==================== Update imports ====================
total_changes = 0

def update_file(filepath, replacements):
    """Apply multiple replacements in a file."""
    global total_changes
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                total_changes += content.count(new)  # approximate
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"  ERR {filepath}: {e}")
    return False

# 1. api_server.py: from api.routes_* → from api.routes.routes_*
print("\n[1] Updating api_server.py...")
changes = []
for f in routes:
    mod = f.replace('.py', '')
    changes.append((f"from api.{mod}", f"from api.routes.{mod}"))
update_file(r"D:\AUTO-EVO-AI-V0.1\api_server.py", changes)

# 2. agent_tools.py: from api.agent_* → from api.agents.agent_*
print("[2] Updating agent_tools.py...")
changes = []
for f in agents:
    mod = f.replace('.py', '')
    changes.append((f"from api.{mod}", f"from api.agents.{mod}"))
update_file(os.path.join(API, 'agent_tools.py'), changes)

# 3. agent_core.py: imports from agent_tools, agent_llm, etc stay, but agent_* cross-refs need update
print("[3] Updating core agent files...")
core_files = ['agent_core.py', 'agent_llm.py', 'agent_concurrent.py']
for cf in core_files:
    cf_path = os.path.join(API, cf)
    if not os.path.exists(cf_path):
        continue
    changes = []
    for f in agents:
        mod = f.replace('.py', '')
        changes.append((f"from api.{mod}", f"from api.agents.{mod}"))
    update_file(cf_path, changes)

# 4. Other agent_*.py in agents/ that import from each other
print("[4] Updating cross-refs in agents/...")
for f in agents:
    agent_path = os.path.join(API, 'agents', f)
    if not os.path.exists(agent_path):
        continue
    changes = []
    for f2 in agents:
        mod = f2.replace('.py', '')
        changes.append((f"from api.{mod}", f"from api.agents.{mod}"))
    # Also update from api.agent_core, api.agent_llm, api.agent_tools - these stay
    changes.append(("from api.agent_core", "from api.agent_core"))
    update_file(agent_path, changes)

# 5. routes_*.py files in routes/ that import from agent_*
print("[5] Updating cross-refs in routes/...")
for f in routes:
    route_path = os.path.join(API, 'routes', f)
    if not os.path.exists(route_path):
        continue
    changes = []
    for f2 in agents:
        mod = f2.replace('.py', '')
        changes.append((f"from api.{mod}", f"from api.agents.{mod}"))
    update_file(route_path, changes)

# 6. api_server.py: also update agent_* imports if any
print("[6] Checking api_server.py for agent imports...")
changes = []
for f in agents:
    mod = f.replace('.py', '')
    changes.append((f"from api.{mod}", f"from api.agents.{mod}"))
update_file(r"D:\AUTO-EVO-AI-V0.1\api_server.py", changes)

# 7. Update startup.py etc.
print("[7] Checking other api/ files...")
for f in stay:
    fp = os.path.join(API, f)
    if not os.path.exists(fp):
        continue
    changes = []
    for f2 in agents:
        mod = f2.replace('.py', '')
        changes.append((f"from api.{mod}", f"from api.agents.{mod}"))
    for f2 in routes:
        mod = f2.replace('.py', '')
        changes.append((f"from api.{mod}", f"from api.routes.{mod}"))
    update_file(fp, changes)

print(f"\nTotal import updates: ~{total_changes}")
print("\n=== DONE ===")
