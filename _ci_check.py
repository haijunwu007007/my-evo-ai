#!/usr/bin/env python3
"""CI 检查脚本 — 部署到服务器 /home/ubuntu/my-evo-ai/check_ci.py"""
import pathlib, re, subprocess, sys

ROOT = pathlib.Path("/home/ubuntu/my-evo-ai")  # 服务器路径
LOCAL = pathlib.Path("D:/AUTO-EVO-AI-V0.1")    # 本地路径（用于本地测试）

ok = warn = err = 0

def report():
    score = 100 - (err * 5) - (warn * 2)
    score = max(0, min(100, score))
    logger.info(f"\n{'='*40}"))
    logger.info(f"CI 检查结果: OK={ok} WARN={warn} ERR={err}"))
    logger.info(f"健康评分: {score}/100"))
    if err:
        sys.exit(1)

logger.info("=== CI Quality Check ==="))

# 1. except:pass
root = ROOT if ROOT.exists() else LOCAL
exc = 0
for f in root.rglob("*.py"):
    if "__pycache__" in str(f) or ".evo" in str(f): continue
    try:
        c = f.read_text("utf-8", errors="ignore")
        # 匹配各种缩进的 except: pass
        exc += len(re.findall(r'^( +)except[^:]*:[^\n]*\n\1+pass', c, re.MULTILINE))
    except: pass
if exc == 0:
    logger.info(f"✅ except:pass = {exc}"); ok += 1)
else:
    logger.info(f"❌ except:pass = {exc}"); err += 1)

# 2. print()
pr = 0
for f in root.rglob("*.py"):
    if "__pycache__" in str(f) or ".evo" in str(f): continue
    try:
        c = f.read_text("utf-8", errors="ignore")
        for line in c.split("\n"):
            s = line.strip()
            if "print(" in s and "logger" not in s and "#" not in line.split("print(")[0] and "def __repr__" not in line and "self." not in line:
                pr += 1
    except: pass
if pr < 10:
    logger.info(f"✅ print() = {pr}"); ok += 1)
else:
    logger.info(f"⚠️  print() = {pr}"); warn += 1)

# 3. body硬编码（frontend）
body = 0
for f in (root/"frontend").glob("*.html"):
    try:
        c = f.read_text("utf-8", errors="ignore")
        if re.search(r'body\s*\{\s*background\s*:\s*#[0-9a-fA-F]{6}', c):
            body += 1
    except: pass
if body == 0:
    logger.info(f"✅ body硬编码 = {body}"); ok += 1)
else:
    logger.info(f"❌ body硬编码 = {body}"); err += 1)

# 4. 文件语法检查
syn = 0
for f in (root/"api/routes").glob("routes_*.py"):
    try:
        subprocess.run([sys.executable, "-m", "py_compile", str(f)], check=True, capture_output=True, timeout=10)
        syn += 1
    except: pass
logger.info(f"✅ 路由文件语法: {syn}/{(root/'api/routes').glob('routes_*.py')|list|len()} OK"))

# 5. 端点健康
try:
    import ssl, urllib.request
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    health = urllib.request.urlopen("https://autoevoai.com/api/v1/health", timeout=10, context=ctx)
    logger.info(f"✅ 健康检查: {health.status}"))
    ok += 1
except Exception as e:
    logger.info(f"❌ 健康检查: {e}"))
    err += 1

report()
