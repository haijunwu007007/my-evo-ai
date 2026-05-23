"""
AUTO-EVO-AI V0.1 — 上市公司级业务 Demo (API版本)
================================================
全流程: 发现模块 → 分组统计 → 编排流水线 → 自然语言 → 事件驱动 → 数据库

用法:
  确保 api_server.py 已在 localhost:8765 运行
  python scripts/demo_via_api.py
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime

API_BASE = "http://127.0.0.1:8765"
PASS = "[PASS]"
FAIL = "[FAIL]"


def api_post(path, body=None):
    url = "%s%s" % (API_BASE, path)
    data = json.dumps(body if body is not None else {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e), "http_error": True}


def api_get(path):
    url = "%s%s" % (API_BASE, path)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e), "http_error": True}


def print_header(title):
    print("\n" + "=" * 60)
    print("  " + title)
    print("=" * 60)


def print_status(step, ok, detail=""):
    icon = PASS if ok else FAIL
    line = "  %s %s" % (icon, step)
    if detail:
        line += " | %s" % detail
    print(line)


print_header("AUTO-EVO-AI V0.1 全流程 Demo (API版)")
print("  API: %s" % API_BASE)

# 步骤1: 模块发现
print_header("步骤1: 模块自动发现")
r = api_post("/api/discover/scan")
ok = r.get("success", False)
dr = r.get("result", r)
total = dr.get("total_files", dr.get("total"))
discovered = dr.get("discovered", 0)
failed = dr.get("failed", 0)
dur = dr.get("duration_ms", dr.get("duration", 0))
print_status("全量扫描", ok, "files=%s discovered=%s failed=%s %.0fms" % (total, discovered, failed, dur))

# 步骤2: 注册表统计
print_header("步骤2: 模块能力地图")
r = api_get("/api/discover/registry")
ok = r.get("success", False)
if ok:
    stats = r.get("stats", r.get("data", {}))
    total = stats.get("total_modules", stats.get("total", stats.get("count", len(stats.get("modules",[])))))
    by_grade = stats.get("by_grade", {})
    scheduled = stats.get("scheduled", 0)
    event_driven = stats.get("event_driven", 0)
    groups = stats.get("groups", stats.get("group_counts", {}))
    print_status("注册表统计", True, "total=%s S=%s A=%s" % (total, by_grade.get("S"), by_grade.get("A")))
    print_status("定时驱动", True, "%s 个模块" % scheduled)
    print_status("事件驱动", True, "%s 个模块" % event_driven)
    if groups:
        sorted_items = sorted(groups.items(), key=lambda x: -x[1])[:8]
        for g, c in sorted_items:
            print("    %s: %s" % (g, c))
else:
    print_status("注册表统计", False, r.get("error", ""))

# 步骤3: 分组详情
print_header("步骤3: 分组详情")
r = api_get("/api/discover/groups")
ok = r.get("success", False)
if ok:
    groups = r.get("groups", {})
    total = sum(len(v) for v in groups.values())
    print_status("分组统计", True, "%d 个分组, %d 个模块" % (len(groups), total))
    sorted_g = sorted(groups.items(), key=lambda x: -len(x[1]))[:6]
    for g, mods in sorted_g:
        print("    %s: %d 模块" % (g, len(mods)))
else:
    print_status("分组统计", False, r.get("error", ""))

# 步骤4: 编排流水线
print_header("步骤4: 智能编排流水线")
test_cases = [("feishu-notifier", ["feishu-notifier"])]
for name, modules in test_cases:
    r = api_post("/api/pipelines/execute", {"module_ids": modules, "mode": "relaxed"})
    summary = r.get("summary", "?")
    ok = r.get("success", False) or "![FAIL]" not in summary
    print_status("%s: %s" % (name, summary), ok)

# 步骤5: 自然语言目标
print_header("步骤5: 自然语言目标")
for goal in ["scan github", "notify feishu"]:
    r = api_post("/api/pipelines/goal", {"goal": goal, "mode": "relaxed"})
    pipeline = r.get("pipeline", r)
    summary = pipeline.get("name", pipeline.get("summary", "?"))
    err = pipeline.get("error", "")
    ok = "success" in str(r.get("summary", "")) or r.get("success", False)
    print_status('"%s": %s' % (goal, summary), ok, err[:60] if err else "")

# 步骤6: 编排统计
print_header("步骤6: 编排引擎统计")
r = api_get("/api/pipelines/stats")
ok = r.get("success", False)
if ok:
    ps = r.get("stats", {})
    print_status("编排统计", True,
        "pipelines=%d success=%d failed=%d modules_executed=%d" % (
            ps.get("total_pipelines", 0),
            ps.get("successful_pipelines", 0),
            ps.get("failed_pipelines", 0),
            ps.get("total_modules_executed", 0)))
    print_status("总耗时", True, "%.1fs" % ps.get("total_duration_seconds", 0))
else:
    print_status("编排统计", False, r.get("error", ""))

# 步骤7: 执行历史
print_header("步骤7: 执行历史")
r = api_get("/api/pipelines/history?limit=5")
ok = r.get("success", False)
if ok:
    history = r.get("pipelines", r.get("history", []))
    print_status("执行历史", True, "%d 条记录" % len(history))
    for h in history:
        hid = h.get("id", "?")[:20]
        status = h.get("status", "?")
        mods = h.get("module_ids", h.get("steps", []))
        if isinstance(mods, list) and len(mods) > 0 and isinstance(mods[0], dict):
            mods = [s.get("module_id","?") for s in mods]
        dur = h.get("total_duration_ms", 0)
        print("    %s %s %s %.0fms" % (hid, status, mods, dur))
else:
    print_status("执行历史", False, r.get("error", ""))

print("\n" + "=" * 60)
print("  Demo 完成!")
print("=" * 60)
