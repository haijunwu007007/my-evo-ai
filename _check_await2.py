import ast, sys
sys.stdout.reconfigure(encoding='utf-8')

for fname in ["api/routes_scheduler.py", "api/startup.py"]:
    with open(fname, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    print(f"\n--- {fname} ---")
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            calls = []
            for n2 in ast.walk(node):
                if isinstance(n2, ast.Await):
                    if hasattr(n2.value, "func") and hasattr(n2.value.func, "attr"):
                        calls.append(f"await {n2.value.func.attr}()")
            if isinstance(node, ast.FunctionDef) and calls:
                print(f"BUG: {node.name()} L{node.lineno}: sync has await: {calls}")
            if isinstance(node, ast.AsyncFunctionDef) and not calls:
                print(f"WARN: {node.name()} L{node.lineno}: async no await")
print("Done")
