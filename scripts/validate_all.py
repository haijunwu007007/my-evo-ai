from pathlib import Path
import py_compile, sys

api_dir = Path("D:/AUTO-EVO-AI-V0.1/api")
all_ok = True
for f in sorted(api_dir.glob("routes_*.py")):
    try:
        py_compile.compile(str(f), doraise=True)
        print(f"  OK: {f.name}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {f.name}: {e}")
        all_ok = False

print(f"\n{'ALL OK' if all_ok else 'SOME FAILED'}")
sys.exit(0 if all_ok else 1)
