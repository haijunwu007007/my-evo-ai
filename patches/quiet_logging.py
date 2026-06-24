"""日志静音补丁"""

# 静音模式
logging.getLogger().setLevel(logging.WARNING)
for l in ['ADAPT', 'APScheduler', 'httpx', 'urllib3', 'httpcore']:
    logging.getLogger(l).setLevel(logging.WARNING)
