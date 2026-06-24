"""日志静音补丁"""
import logging
# 根logger杀干净
logging.getLogger().setLevel(logging.WARNING)
# 全部第三方库静音
for l in ['ADAPT', 'APScheduler', 'httpx', 'urllib3', 'httpcore', 'chardet', 'requests',
          'PIL', 'boto3', 'botocore', 's3transfer', 'openai', 'httpcore.http11',
          'matplotlib', 'fsspec', 's3fs', 'asyncio', 'aiosqlite',
          'evo', 'evo.modules', 'evo.agents', 'evo.api']:
    logging.getLogger(l).setLevel(logging.WARNING)
# 模块级的日志也压制
for l in ['agent_sentinel_v4', 'ocr_engine', 'graph_engine', 'api_routes']:
    logging.getLogger(l).setLevel(logging.WARNING)
logging.getLogger('root').setLevel(logging.WARNING)
