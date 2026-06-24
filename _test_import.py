import sys
sys.path.insert(0,"/home/ubuntu/my-evo-ai")
try:
    from modules.qodo_review import QodoReviewModule
    m=QodoReviewModule()
    print("qodo OK:", m.get_status())
except Exception as e:
    print("qodo FAIL:", e)
try:
    from modules.testsigma_agent import TestSigmaModule
    m=TestSigmaModule()
    print("testsigma OK:", m.get_status())
except Exception as e:
    print("testsigma FAIL:", e)
