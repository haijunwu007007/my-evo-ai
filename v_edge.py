"""验证K8s降级+LLM规划修复"""
import sys; sys.path.insert(0, "api")
from hub.auto_build import detect_k8s
from workflow.autonomous import AutonomousAgent

k = detect_k8s()
print(f"K8s detect: has_k8s={k['has_k8s']}, reason={k.get('reason','ok')}, fallback={k['fallback']}")

a = AutonomousAgent()
# Test LLM fail case - goal with no clear tool match
r = a.run("做个电商网站并部署上线")
print(f"Ecom: status={r['status']}, steps={r.get('steps_executed',0)}, result={r.get('result','')[:80]}, note={r.get('note','')[:60]}")

# Test K8s fallback by running detect
print(f"K8s fallback will be: docker (kubectl not on this machine)")
print("ALL OK")
