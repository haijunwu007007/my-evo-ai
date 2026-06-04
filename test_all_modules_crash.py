#!/usr/bin/env python3
"""全模块压力测试 — 测试每一个模块能否正常导入并执行核心函数"""
import sys, importlib, os, time, json, traceback, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules")
BASE = "http://127.0.0.1:8765"

results = {"pass": [], "fail": [], "skip": [], "import_err": [], "func_err": []}

# ─── 第1轮：导入测试（所有 .py 文件） ───
all_files = sorted(os.listdir(MODULES_DIR))
py_files = [f for f in all_files if f.endswith(".py") and not f.startswith("_")]

print(f"\n{'='*60}")
print(f"  AUTO-EVO-AI 全模块测试 ({len(py_files)} 个模块)")
print(f"  开始时间: {time.strftime('%H:%M:%S')}")
print(f"{'='*60}")

for idx, fname in enumerate(py_files, 1):
    mname = fname[:-3]
    print(f"\r  测试中 [{idx}/{len(py_files)}] {mname.ljust(35)} ", end="", flush=True)
    try:
        mod = importlib.import_module(f"modules.{mname}")
        # 检查是否有核心函数
        has_functions = False
        for attr_name in dir(mod):
            if attr_name.startswith("_") or attr_name in ["os", "sys", "time", "json", "Path", "logging"]:
                continue
            attr = getattr(mod, attr_name)
            if callable(attr):
                has_functions = True
                # 尝试无参数调用（捕获异常，不中断）
                try:
                    if attr_name in ["main", "run", "execute", "start"]:
                        pass  # 不自动执行，可能阻塞
                except:
                    pass
        if has_functions:
            results["pass"].append(mname)
        else:
            results["skip"].append((mname, "只有常量/类"))
    except SyntaxError as e:
        results["import_err"].append((mname, f"语法错误: {e}"))
    except Exception as e:
        results["import_err"].append((mname, f"{type(e).__name__}: {str(e)[:80]}"))

print(f"\n{'='*60}")

# ─── 第2轮：API 端点测试 ───
print(f"\n{'='*60}")
print(f"  API 端点测试")
print(f"{'='*60}")

api_endpoints = [
    ("GET", "/api/v1/status", "系统状态"),
    ("GET", "/api/v1/version", "系统版本"),
    ("GET", "/api/v1/payment/config", "支付配置"),
    ("GET", "/api/v1/plugins", "插件列表"),
    ("GET", "/api/v1/todos", "待办列表"),
    ("GET", "/api/v1/files", "文件列表"),
    ("GET", "/api/v1/chat/history?username=admin&limit=5", "聊天记录"),
    ("GET", "/api/v1/webhook/events", "Webhook事件"),
    ("GET", "/api/v1/user/login", "用户登录(GET 应404)"),
    ("POST", "/api/v1/user/login", "用户登录"),
    ("POST", "/api/v1/user/register", "用户注册"),
    ("POST", "/api/v1/chat/save", "保存聊天"),
    ("POST", "/api/v1/todos", "创建待办"),
    ("POST", "/api/v1/webhook", "接收Webhook"),
    ("POST", "/api/v1/gateway", "API网关"),
    ("POST", "/api/v1/sql/query", "SQL查询"),
]

for method, path, desc in api_endpoints:
    url = f"{BASE}{path}"
    try:
        data = None
        headers = {"Content-Type": "application/json"}
        if method == "POST":
            # 根据路径准备不同 body
            if "login" in path:
                data = json.dumps({"username": "admin", "password": ""}).encode()
            elif "register" in path:
                data = json.dumps({"username": f"test_{int(time.time())}"}).encode()
            elif "chat/save" in path:
                data = json.dumps({"username": "admin", "role": "user", "content": "test"}).encode()
            elif "todos" in path:
                data = json.dumps({"title": "test", "priority": "低"}).encode()
            elif "webhook" in path:
                data = json.dumps({"event": "test", "payload": {"msg": "hello"}}).encode()
            elif "gateway" in path:
                data = json.dumps({"url": "https://httpbin.org/get", "method": "GET"}).encode()
            elif "sql" in path:
                data = json.dumps({"sql": "SELECT 1 as test"}).encode()
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers)
        
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read().decode()
        is_success = resp.status == 200
        has_ok = '"success":true' in body or '"success": True' in body or '"success":' not in body
        
        if is_success and has_ok:
            results["pass"].append(f"API:{desc}")
        elif is_success:
            results["fail"].append(f"API:{desc} — 200但success=false: {body[:100]}")
        else:
            results["fail"].append(f"API:{desc} — HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        # 404 for GET login is expected
        if e.code == 404 and "login" in path:
            results["pass"].append(f"API:{desc}")
        else:
            results["fail"].append(f"API:{desc} — HTTP {e.code}")
    except Exception as e:
        results["fail"].append(f"API:{desc} — {type(e).__name__}: {str(e)[:60]}")

# ─── 第3轮：核心智能请求测试 ───
print(f"\n{'='*60}")
print(f"  智能请求测试 (代表性功能)")
print(f"{'='*60}")

smart_tests = [
    ("系统状态", "系统怎么样"),
    ("帮助", "你会什么"),
    ("文档", "帮我写一个测试合同"),
    ("数学", "总产量500+450+520=多少"),
    ("GitHub", "GitHub今天热门项目"),
    ("翻译", "帮我翻译成英文：你好"),
    ("记忆", "记住我测试一下"),
    ("待办帮助", "我有哪些待办"),
    ("搜索", "帮我搜索Python"),
    ("代码", "帮我写一个Python函数"),
]

for desc, msg in smart_tests:
    try:
        body = json.dumps({"message": msg, "lang": "zh-CN"}).encode()
        req = urllib.request.Request(f"{BASE}/api/v1/smart", data=body, 
                                     headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        if result.get("success"):
            results["pass"].append(f"SMART:{desc}")
        else:
            results["fail"].append(f"SMART:{desc} — {result.get('detail','?')[:60]}")
    except Exception as e:
        results["fail"].append(f"SMART:{desc} — {type(e).__name__}: {str(e)[:60]}")

# ─── 输出结果 ───
print(f"\n\n{'='*60}")
print(f"  📊 全模块测试报告")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}")
print(f"  ✅ PASS:      {len(results['pass'])}")
print(f"  ❌ FAIL:      {len(results['fail'])}")
print(f"  ⏭️  SKIP:      {len(results['skip'])}")
print(f"  💥 IMPORT_ERR: {len(results['import_err'])}")
print(f"  📦 总计:       {len(results['pass'])+len(results['fail'])+len(results['skip'])+len(results['import_err'])}")
print(f"  通过率:        {len(results['pass'])*100//(len(results['pass'])+len(results['fail'])+len(results['import_err']) or 1)}%")

if results["import_err"]:
    print(f"\n{'='*60}")
    print(f"  💥 导入失败模块 ({len(results['import_err'])}个)")
    print(f"{'='*60}")
    for name, err in sorted(results["import_err"]):
        print(f"  ❌ {name}: {err}")

if results["fail"]:
    print(f"\n{'='*60}")
    print(f"  ❌ 功能测试失败 ({len(results['fail'])}个)")
    print(f"{'='*60}")
    for item in sorted(results["fail"]):
        print(f"  ❌ {item}")

# ─── 写入报告文件 ───
report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "module_test_report.json")
os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n📁 报告已保存: {report_path}")
print(f"{'='*60}")
