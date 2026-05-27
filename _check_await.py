"""Check scheduler_engine for await mismatches"""
import ast, sys
sys.stdout.reconfigure(encoding='utf-8')

with open("core/scheduler_engine.py", encoding="utf-8") as f:
    src = f.read()

tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
        calls = []
        for n2 in ast.walk(node):
            if isinstance(n2, ast.Await):
                if hasattr(n2.value, "func") and hasattr(n2.value.func, "attr"):
                    calls.append(f"  await {n2.value.func.attr}() L{n2.lineno}")
        if isinstance(node, ast.AsyncFunctionDef):
            if not calls:
                print(f"WARN: async {node.name}() L{node.lineno}: no await")
        else:
            if calls:
                print(f"BUG: sync {node.name}() L{node.lineno}: has await! {''.join(calls)}")
print("Done")
