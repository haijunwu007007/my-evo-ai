"""Check class structure of agent_orchestrator and sub-modules"""
import ast, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

for fn in ["modules/agent_orchestrator.py", "modules/_base/orchestrator_types.py",
            "modules/_base/orchestrator_intent.py", "modules/_base/orchestrator_execution.py"]:
    with open(fn, encoding="utf-8", errors="replace") as f:
        src = f.read()
    tree = ast.parse(src)
    classes = [f"{n.name}(L{n.lineno})" for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    print(f"{fn}: {len(src)//1024}KB, {len(lines := src.splitlines())} lines")
    for c in classes:
        print(f"  {c}")
