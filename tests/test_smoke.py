"""
AUTO-EVO-AI V0.1 — 冒烟测试
覆盖核心API端点的可用性
"""
import os, sys, json, urllib.request, ssl, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get("EVO_TEST_URL", "http://localhost:8765")
TIMEOUT = 10
FAILED = 0
PASSED = 0

def check(path, desc="", expect=200, method="GET", body=None):
    global PASSED, FAILED
    url = f"{BASE_URL}{path}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method,
            headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        status = resp.status
        if status == expect:
            PASSED += 1
            print(f"  ✅ {method} {path} = {status} {desc}")
        else:
            FAILED += 1
            print(f"  ❌ {method} {path} = {status} (期望 {expect}) {desc}")
    except urllib.error.HTTPError as e:
        if e.code == expect:
            PASSED += 1
            print(f"  ✅ {method} {path} = {e.code} {desc}")
        else:
            FAILED += 1
            print(f"  ❌ {method} {path} = {e.code} (期望 {expect}) {desc}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {method} {path} = 异常: {e} {desc}")

print(f"=== AUTO-EVO-AI 冒烟测试 ===")
print(f"目标: {BASE_URL}\n")

# ── 基础 ──
check("/api/v1/health", "健康检查")
check("/api/v1/version", "版本信息")

# ── 首页 ──
check("/", "首页")
check("/chat.html", "聊天页面")

# ── 核心功能 ──
check("/api/v1/status", "系统状态")
check("/api/v1/llm/default", "LLM默认模型")

# ── 页面路由 ──
for p in ["/enterprise.html", "/workflow", "/deploy", "/video", "/agents",
          "/skills", "/experts", "/settings", "/hub", "/admin",
          "/canvas", "/creative", "/billion-os.html", "/n8n-browse",
          "/channel", "/desktop"]:
    check(p, f"页面 {p}")

# ── API 端点 ──
check("/api/v1/modules", "模块列表")
check("/api/v1/plugins", "插件列表")
check("/api/v1/rag/kb", "知识库列表")
check("/api/v1/notify/channels", "通知渠道")
check("/api/v1/github/stats", "GitHub扫描统计")
check("/api/v1/evo/summary", "进化引擎概要")

print(f"\n=== 结果: {PASSED} 通过, {FAILED} 失败 ===")
sys.exit(0 if FAILED == 0 else 1)
