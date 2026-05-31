import os
import sys, os, inspect
BASE = r'os.environ.get("EVO_HOME", ".")'
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, 'modules'))

from _base.enterprise_module import EnterpriseModule
from _base.module_meta import BaseModule

targets = [
    'access_control','aegis_governance','agent_apollo','cache_engine',
    'task_center','memory_manager'
]
oks, issues = 0, 0

for mname in targets:
    try:
        mod = __import__(mname)
        for cname, cls in inspect.getmembers(mod, inspect.isclass):
            if cls in (EnterpriseModule, BaseModule) or not issubclass(cls, (EnterpriseModule, BaseModule)):
                continue
            meta = getattr(cls, '__module_meta__', {})
            inp = meta.get('inputs', [])
            names = [x.get('name','') for x in inp]
            dups = len(names) - len(set(names))
            if dups:
                print(f'FAIL {mname}.{cname}: {dups} dups in {len(names)} inputs')
                issues += 1
            else:
                print(f'PASS {mname}.{cname}: {len(inp)} inputs, 0 dups')
                oks += 1
            break
    except Exception as e:
        print(f'ERR  {mname}: {e}')

print(f'\nSummary: {oks} pass, {issues} fail')
