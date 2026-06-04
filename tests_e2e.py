# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 端到端测试 — 5 条核心链路"""
import json, urllib.request, sys, time, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8765"

def api(method, path, body=None):
    b = json.dumps(body).encode() if body else None
    r = urllib.request.urlopen(urllib.request.Request(f"{BASE}{path}", data=b,
        headers={"Content-Type":"application/json"} if body else {},
        method=method), timeout=60)
    return json.loads(r.read())

ok = 0; fail = 0
def check(name, cond, detail=""):
    global ok, fail
    if cond: ok+=1; print(f"  ✅ {name}")
    else: fail+=1; print(f"  ❌ {name}: {detail}")

print(f"\n{'='*60}")
print(f"  AUTO-EVO-AI V0.1 端到端测试")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}")

# 1. 系统状态链路
print(f"\n--- 1/5: 系统状态链路 ---")
s = api("GET", "/api/v1/status")
check("API 返回成功", s.get("success"), str(s))
check("483 模块注册", s.get("modules_total")>=480, str(s.get("modules_total")))
check("系统版本 V0.1", s.get("api_version")=="V0.1", s.get("api_version"))

# 2. 智能聊天链路 (文档生成)
print(f"\n--- 2/5: 智能聊天链路 (文档生成) ---")
r = api("POST", "/api/v1/smart", {"message":"帮我写一份测试合同", "lang":"zh-CN"})
check("聊天返回成功", r.get("success"), str(r)[:80])
check("生成了文档", "合同已生成" in str(r.get("result","")) or "Word" in str(r.get("result","")), str(r.get("result",""))[:60])

# 3. 智能聊天链路 (GitHub 查询)
print(f"\n--- 3/5: 智能聊天链路 (GitHub查询) ---")
r = api("POST", "/api/v1/smart", {"message":"GitHub今天热门项目", "lang":"zh-CN"})
check("GitHub查询成功", r.get("success"), str(r)[:80])
check("返回了项目列表", "GitHub" in str(r.get("result","")) and "⭐" in str(r.get("result","")), str(r.get("result",""))[:60])

# 4. 文件操作链路  
print(f"\n--- 4/5: 文件操作链路 ---")
# 用户注册
r = api("POST", "/api/v1/user/register", {"username":"test_e2e"})
check("注册成功", r.get("success"), str(r))
# 聊天记录保存
r = api("POST", "/api/v1/chat/save", {"username":"test_e2e","role":"user","content":"你好"})
check("聊天记录保存", r.get("success"), str(r))
# 查询聊天记录
r = api("GET", "/api/v1/chat/history?username=test_e2e")
check("聊天记录查询", r.get("success"), str(r)[:60])
check("至少有一条记录", len(r.get("messages",[]))>0, str(len(r.get("messages",[]))))

# 5. 功能路由链路
print(f"\n--- 5/5: 功能路由链路 ---")
r = api("GET", "/api/v1/payment/config")
check("支付配置", r.get("success"), str(r)[:60])
r = api("GET", "/api/v1/plugins")
check("插件列表", r.get("success"), str(r)[:60])
r = api("POST", "/api/v1/webhook", {"event":"e2e_test","payload":{"ok":True}})
check("Webhook接收", r.get("success"), str(r)[:60])

print(f"\n{'='*60}")
print(f"  ✅ {ok} 通过 | ❌ {fail} 失败 | 总计 {ok+fail}")
grade = "🏆 ALL PASS" if fail==0 else "⚠️ 有失败"
print(f"  等级: {grade}")
print(f"{'='*60}")
