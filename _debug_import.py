"""调试 agent_planner 导入"""
import sys, traceback, os
sys.path.insert(0, os.path.dirname(__file__))
try:
    import modules.agent_planner
    print(f"OK: class={modules.agent_planner.__name__}")
except Exception:
    traceback.print_exc()

print("---")

# Also try geo_search
try:
    import modules.geo_search
    print(f"OK: class={modules.geo_search.__name__}")
except Exception:
    traceback.print_exc()
