import os, re
from collections import defaultdict

mod_dir = r'D:\AUTO-EVO-AI-V0.1\modules'

# 关键第三方库
REAL_DEPS = {
    # HTTP/网络
    'requests', 'aiohttp', 'urllib3', 'httpx', 'httplib2',
    # 数据库
    'psycopg2', 'sqlalchemy', 'pymongo', 'redis', 'aiomysql', 'asyncpg',
    'aiosqlite', 'mysql.connector', 'pymysql', 'tinydb',
    # 消息队列
    'kafka', 'pika', 'celery', 'rabbitmq',
    # 云服务
    'boto3', 'google.cloud', 'azure', 'tencentcloud',
    # AI/LLM
    'openai', 'anthropic', 'google.generativeai', 'zhipuai',
    # 浏览器自动化
    'playwright', 'selenium',
    # 监控
    'psutil', 'prometheus_client',
    # 数据处理
    'pandas', 'numpy', 'matplotlib',
    # Docker/K8s
    'docker', 'kubernetes',
    # 文件
    'watchdog', 'python-docx', 'openpyxl',
    # 系统
    'cryptography', 'jwt', 'yaml',
}

modules_with_real_deps = []
modules_without_real_deps = []

for f in sorted(os.listdir(mod_dir)):
    if not f.endswith('.py') or f.startswith('_'):
        continue
    name = f.replace('.py', '')
    fp = os.path.join(mod_dir, f)
    size = os.path.getsize(fp)
    try:
        content = open(fp, encoding='utf-8', errors='ignore').read()
    except:
        content = ''

    # 检查是否 import 了真实第三方库
    found_libs = set()
    for lib in REAL_DEPS:
        for pattern in [
            f'import {lib}',
            f'from {lib}',
            f'import {lib}.',
            f'from {lib}.',
        ]:
            if pattern in content:
                found_libs.add(lib)
                break

    if found_libs:
        modules_with_real_deps.append((name, size, found_libs))
    else:
        modules_without_real_deps.append((name, size))

print(f'===== 有真实第三方依赖的模块: {len(modules_with_real_deps)} =====')
for name, size, libs in sorted(modules_with_real_deps):
    print(f'  {name} ({size//1024}KB): {", ".join(sorted(libs))}')

print(f'\n===== 无真实第三方依赖的模块: {len(modules_without_real_deps)} =====')
for name, size in modules_without_real_deps[:30]:
    print(f'  {name} ({size//1024}KB)')
if len(modules_without_real_deps) > 30:
    print(f'  ... 还有 {len(modules_without_real_deps) - 30} 个')
