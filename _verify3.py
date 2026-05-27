import sys, os
sys.path.insert(0, '.')
from modules.system_monitor import SystemMonitorModule
m = SystemMonitorModule()
lines = len(open('modules/system_monitor.py', encoding='utf-8').readlines())
print(f'system_monitor: OK, {lines} lines, delegate={m.delegate is not None}')

from modules.sso_auth import SsoAuth
sa = SsoAuth()
lines2 = len(open('modules/sso_auth.py', encoding='utf-8').readlines())
print(f'sso_auth: OK, {lines2} lines, delegate={sa.delegate is not None}')

# data_analysis
import importlib
spec = importlib.util.spec_from_file_location('da', 'modules/data_analysis.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
da = mod.DataAnalysis()
lines3 = len(open('modules/data_analysis.py', encoding='utf-8').readlines())
print(f'data_analysis: OK, {lines3} lines, delegate={da.delegate is not None}')
print('ALL THREE MODULES OK')
