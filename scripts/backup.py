"""
AUTO-EVO-AI 灾备工具 — 保存模块元数据 + 关键配置到备份目录
"""
import os, shutil, json, datetime
BASE = "D:/AUTO-EVO-AI-V0.1"
BACKUP = "D:/AUTO-EVO-AI_BACKUPS"
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
dst = os.path.join(BACKUP, ts)

# Key files to backup
keys = [
    "api_server.py", "config.yaml", ".env", ".api_key",
    "i18n.js", "wizard.html", "ops_panel.html", "index.html",
    "Dockerfile", "docker-compose.yml", "README.md",
    "core", "modules", "docs", "tests",
]
for k in keys:
    src = os.path.join(BASE, k)
    if os.path.isfile(src):
        os.makedirs(os.path.dirname(os.path.join(dst, k)), exist_ok=True)
        shutil.copy2(src, os.path.join(dst, k))
    elif os.path.isdir(src):
        shutil.copytree(src, os.path.join(dst, k), dirs_exist_ok=True)

# Module manifest
mods = [f for f in os.listdir(os.path.join(BASE, "modules")) if f.endswith(".py")]
with open(os.path.join(dst, "manifest.json"), "w") as f:
    json.dump({"timestamp": ts, "modules": len(mods), "files": keys}, f, indent=2)
print(f"Backup saved: {dst} ({len(mods)} modules)")
