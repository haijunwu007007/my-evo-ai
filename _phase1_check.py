"""Phase 1 检查：验证所有核心文件语法正确"""
import ast
import pathlib

base = pathlib.Path(r"D:\AUTO-EVO-AI-V0.1")

# 1. 检查 core/*.py 语法
print("=" * 50)
print("1. core/ 语法检查")
print("=" * 50)
bad = []
for f in sorted(base.glob("core/*.py")):
    try:
        ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError as e:
        bad.append((f.name, str(e)))

total_core = sum(1 for _ in base.glob("core/*.py"))
print(f"core/ 文件数: {total_core}")
print(f"语法错误: {len(bad)}")
for name, err in bad:
    print(f"  FAIL {name}: {err}")
if not bad:
    print("  ALL OK")

# 2. 检查 api/*.py 语法
print()
print("=" * 50)
print("2. api/ 语法检查")
print("=" * 50)
bad2 = []
for f in sorted(base.glob("api/*.py")):
    try:
        ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError as e:
        bad2.append((f.name, str(e)))

total_api = sum(1 for _ in base.glob("api/*.py"))
print(f"api/ 文件数: {total_api}")
print(f"语法错误: {len(bad2)}")
for name, err in bad2:
    print(f"  FAIL {name}: {err}")
if not bad2:
    print("  ALL OK")

# 3. 检查 api_server.py
print()
print("=" * 50)
print("3. api_server.py 语法检查")
print("=" * 50)
try:
    ast.parse((base / "api_server.py").read_text(encoding="utf-8"))
    print("  ALL OK")
except SyntaxError as e:
    print(f"  FAIL: {e}")

# 4. 尝试 import 核心引擎（快速冒烟）
print()
print("=" * 50)
print("4. 核心引擎 import 冒烟测试")
print("=" * 50)
import sys
sys.path.insert(0, str(base))
sys.path.insert(0, str(base / "modules"))

engines = [
    "core.data_layer",
    "core.message_bus",
    "core.auth_provider",
    "core.logging_config",
    "core.module_manager",
    "core.llm_gateway",
    "core.scheduler_engine",
    "core.pipeline_engine",
    "core.task_queue_engine",
    "core.event_engine",
    "core.config_center",
    "core.external_services",
    "core.doc_generator",
    "core.cicd_engine",
    "core.ws_engine",
    "core.evo_brain",
]

for eng in engines:
    try:
        __import__(eng)
        print(f"  OK   {eng}")
    except Exception as e:
        print(f"  FAIL {eng}: {e}")

print()
print("DONE")
