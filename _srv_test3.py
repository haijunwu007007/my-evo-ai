import sys, os
# Don't chdir to my-evo-ai to avoid loading the full system
sys.path.insert(0, "/home/ubuntu/my-evo-ai")
try:
    from modules.qodo_review import QodoReviewModule
    m = QodoReviewModule()
    print("IMPORT OK", m.get_status())
except Exception as e:
    print("IMPORT FAIL", type(e).__name__, str(e)[:200])
