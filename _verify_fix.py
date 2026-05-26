"""验证所有模块真实化改造后的 import 正确性"""
import sys, os, importlib
sys.path.insert(0, r'D:\AUTO-EVO-AI-V0.1')
sys.path.insert(0, r'D:\AUTO-EVO-AI-V0.1/modules')

modules_to_check = [
    # 已修改的模块
    'secret_manager',
    'llm_openai',
    'redis_cache',
    'docker_manager',
    'k8s_orch',
    'postgres_db',
    'database_connector',
    'notion_sync',
    # 核心引擎
    'core.event_engine',
    'core.scheduler_engine',
    'core.pipeline_engine',
    'core.task_queue_engine',
]

import sys
sys.stdout.reconfigure(encoding='utf-8')

print('=' * 60)
print('验证模块真实化改造 import 正确性')
print('=' * 60)

ok = 0
fail = 0
for mod in modules_to_check:
    try:
        importlib.import_module(mod)
        print(f'  OK: {mod}')
        ok += 1
    except Exception as e:
        err = str(e).split('\n')[0][:120]
        print(f'  FAIL: {mod} => {err}')
        fail += 1

print(f'\nPass: {ok}/{ok+fail}')
if fail > 0:
    print(f'Failed: {fail}')
    
print('\n' + '=' * 60)
print('第三方库可用性检查')
print('=' * 60)
checks = [
    ('cryptography', 'secret_manager'),
    ('openai', 'llm_openai'),
    ('redis', 'redis_cache'),
    ('docker', 'docker_manager'),
    ('kubernetes', 'k8s_orch'),
    ('psycopg2', 'postgres_db/database_connector'),
    ('requests', 'notion_sync'),
]
for lib, usage in checks:
    try:
        importlib.import_module(lib)
        print(f'  OK: {lib}')
    except ImportError:
        print(f'  MISSING: {lib} (降级模式)')
