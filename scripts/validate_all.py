from pathlib import Path
import py_compile, sys

api_dir = Path(__file__).resolve().parent.parent / "api"
all_ok = True
for f in sorted(api_dir.glob("routes_*.py")):
    try:
        py_compile.compile(str(f), doraise=True)
        logger.info(f"  OK: {f.name}"))
    except py_compile.PyCompileError as e:
        logger.info(f"  FAIL: {f.name}: {e}"))
        all_ok = False

logger.info(f"\n{'ALL OK' if all_ok else 'SOME FAILED'}"))
sys.exit(0 if all_ok else 1)
