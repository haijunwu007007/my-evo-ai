import sys, os
sys.path.insert(0, r'C:\Users\吴海军\yuanqiai\my-evo-ai')
sys.path.insert(0, r'C:\Users\吴海军\yuanqiai\my-evo-ai\modules')
try:
    from modules._base.module_meta import EnterpriseModule
    print('SUCCESS: EnterpriseModule imported')
except Exception as e:
    import traceback
    traceback.print_exc()
