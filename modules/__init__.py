"""AUTO-EVO-AI module package. Auto-scans and registers modules."""
import os, sys, importlib, logging, time
logger = logging.getLogger("evo.modules")

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_registered_modules = []

def scan_and_register():
    """Background scan all .py files in modules/ and try to register"""
    global _registered_modules
    count = 0
    for f in sorted(os.listdir(_MODULE_DIR)):
        if not f.endswith(".py") or f.startswith("_") or f == "__init__.py":
            continue
        name = f[:-3]
        try:
            spec = importlib.util.spec_from_file_location(name, os.path.join(_MODULE_DIR, f))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f"modules.{name}"] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, "__module_meta__"):
                    _registered_modules.append(name)
                    count += 1
        except Exception as ex:
            logger.debug(f"Module {name} skipped: {ex}")
    logger.info(f"Scanned {len(os.listdir(_MODULE_DIR))} files, registered {count} modules")
    return count

# Auto-run on import
scan_and_register()
