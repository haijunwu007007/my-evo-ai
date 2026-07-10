import os
import sys, os
sys.path.insert(0, r'os.environ.get("EVO_HOME", ".")')
sys.path.insert(0, r'os.environ.get("EVO_HOME", ".")\modules')
try:
    from modules._base.module_meta import EnterpriseModule
    logger.info('SUCCESS: EnterpriseModule imported'))
except Exception as e:
    import traceback
    traceback.print_exc()
