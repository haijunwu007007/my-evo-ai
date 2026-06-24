import sys, os
os.chdir("/home/ubuntu/my-evo-ai")
sys.path.insert(0, ".")

try:
    from modules.qodo_review import QodoReviewModule
    m = QodoReviewModule()
    print("IMPORT OK", m.get_status())
except Exception as e:
    import traceback
    print("IMPORT FAIL:", str(e))
    traceback.print_exc()
