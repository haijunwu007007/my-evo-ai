"""AUTO-EVO-AI V0.1 — 模块分类映射表"""
CATEGORY_MAP = {
    # Agent
    "AGENT": "智能体",
    "AGENCY": "智能体", "AGENTGUARD": "安全", "AGENTSEEK": "智能体",
    "CREWAI": "智能体", "AUTONOMOUS": "智能体", "SUPERAGENT": "智能体",
    # AI / LLM
    "AI": "AI引擎", "LLM": "AI引擎", "RAG": "AI引擎", "EMBEDDING": "AI引擎",
    "MODEL": "AI引擎", "ML": "AI引擎", "RERANK": "AI引擎",
    # 数据处理
    "DATA": "数据处理", "DATABASE": "数据处理", "TABLE": "数据处理",
    "SQL": "数据处理", "QUERY": "数据处理", "STREAM": "数据处理",
    "CACHE": "数据处理", "INDEX": "数据处理", "SCHEMA": "数据处理",
    "UNSTRUCTUR": "数据处理", "SORT": "数据处理", "SHARDING": "数据处理",
    # 基础设施
    "DOCKER": "基础设施", "K8S": "基础设施", "CLUSTER": "基础设施",
    "NETWORK": "基础设施", "STORAGE": "基础设施", "DNS": "基础设施",
    "VPN": "基础设施", "TUNNEL": "基础设施", "PROXY": "基础设施",
    "LOAD": "基础设施", "DEPLOY": "基础设施",
    # 安全
    "SECURITY": "安全", "PERMISSION": "安全", "AUDIT": "安全",
    "THREAT": "安全", "WAF": "安全", "SSL": "安全",
    "AEGIS": "安全", "SECRET": "安全", "SIGNED": "安全",
    # 运维
    "BACKUP": "运维", "MONITOR": "运维", "ALERT": "运维",
    "INCIDENT": "运维", "HEALTH": "运维", "PERF": "运维",
    "REPLICATION": "运维", "RETENTION": "运维", "SLA": "运维",
    "AIOPS": "运维", "SCAN": "运维", "CHAOS": "运维",
    # CI/CD
    "CI": "CICD", "CD": "CICD", "RELEASE": "CICD",
    "BUILD": "CICD", "DEPLOY": "CICD", "ROLLBACK": "CICD",
    "TERRAFORM": "CICD", "ANSIBLE": "CICD", "ARGOCD": "CICD",
    # 通信
    "MESSAGE": "通信", "MQ": "通信", "QUEUE": "通信",
    "NOTIFY": "通信", "EMAIL": "通信", "TELEGRAM": "通信",
    "WEBHOOK": "通信", "SSE": "通信", "WS": "通信",
    # 调度
    "SCHEDULER": "调度", "CRON": "调度", "TASK": "调度",
    "TRIGGER": "调度", "WORKFLOW": "调度",
    # 配置
    "CONFIG": "配置", "REGISTRY": "配置",
    # 存储
    "MEMORY": "存储", "CACHE": "存储", "BLOB": "存储",
    "OBJECT": "存储", "TEMP": "存储",
    # 前端/UI
    "UI": "前端", "PAGE": "前端", "THEME": "前端",
    # 文档
    "DOCUMENT": "文档", "KNOWLEDGE": "文档",
    # 代码
    "CODE": "代码", "GIT": "代码", "VERSIONING": "代码",
    # 自动化
    "AUTO": "自动化", "RPA": "自动化",
    # 监控
    "LOG": "监控", "METRIC": "监控", "TRACE": "监控",
    "SLOW": "监控", "INCIDENT": "监控",
    # 集成
    "API": "集成", "PLUGIN": "集成", "CONNECTION": "集成",
    "SSO": "集成", "OAUTH": "集成",
    # 系统
    "SYSTEM": "系统", "EVO": "系统", "CROSS": "系统",
    # 音视频
    "VOICE": "音视频", "AUDIO": "音视频", "VIDEO": "音视频",
    "TTS": "音视频", "TRANSLATION": "音视频",
    # 时间
    "TIME": "时间", "TEMPORAL": "时间", "TTL": "时间",
    # 资源管理
    "RESOURCE": "资源", "COST": "资源", "BILLING": "资源",
    # 网络
    "IP": "网络", "DNS": "网络", "CDN": "网络",
    # 会话
    "SESSION": "会话", "STATE": "会话",
    # 交易
    "TRANSACTION": "交易", "SAGA": "交易",
    # 体验
    "EXPERIENCE": "体验", "FEEDBACK": "体验",
    # 其他杂类——保持原名
    "ACCESS": "访问控制", "ATOM": "原子操作",
    "BROWSER": "浏览器", "WINDOW": "窗口",
    "DEPENDENCY": "依赖管理", "FILE": "文件",
    "IDEMPOTENT": "幂等", "INJECTION": "注入",
    "MCP": "MCP协议", "PROJECT": "项目管理",
    "REPORT": "报告", "REQUEST": "请求管理",
    "SERVICE": "服务治理", "STOCK": "股票",
    "WEAVIATE": "向量数据库",
}


def normalize_category(raw: str) -> str:
    """将分类前缀映射为标准业务域"""
    raw_upper = raw.upper()
    mapped = CATEGORY_MAP.get(raw_upper)
    if mapped:
        return mapped
    # 尝试去掉末尾数字
    stripped = raw_upper.rstrip("0123456789")
    if stripped and stripped != raw_upper:
        mapped = CATEGORY_MAP.get(stripped)
        if mapped:
            return mapped
    return raw.capitalize()
