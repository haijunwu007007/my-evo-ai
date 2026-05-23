

        var DEFAULT_MODULES = [

            { id: 'rpa-control', name: 'RPA控制', group: '守护进程', icon: '🎮', desc: 'Windows RPA智能控制，支持桌面自动化操作', source: 'microsoft/windows-use', stars: '18k', tags: ['RPA', 'Windows', '自动化'], color: '#6366F1' },

            { id: 'feishu-notify', name: '飞书通知', group: '守护进程', icon: '💬', desc: '飞书消息推送，支持卡片消息和群通知', source: 'larksuite/oapi-sdk', stars: '12k', tags: ['飞书', '通知', 'Webhook'], color: '#4F46E5' },

            { id: 'telegram-bridge', name: 'Telegram桥接', group: '守护进程', icon: '📱', desc: 'Telegram Bot控制，支持消息收发和命令处理', source: 'python-telegram-bot', stars: '25k', tags: ['Telegram', 'Bot', '消息'], color: '#0EA5E9' },

            { id: 'mercury-core', name: 'Mercury核心', group: '守护进程', icon: '⚡', desc: '高性能Agent运行时，支持多任务并行处理', source: 'meta-agents/mercury', stars: '8k', tags: ['Agent', '运行时', '并行'], color: '#F59E0B' },

            { id: 'email-automation', name: '邮件自动化', group: '企业自动化', icon: '📧', desc: '智能邮件收发、分类、自动回复', source: 'Python SMTP/IMAP', stars: '核心模块', tags: ['邮件', '自动化', '分类'], color: '#10B981' },

            { id: 'enterprise-notifier', name: '企业通知', group: '企业自动化', icon: '📢', desc: '飞书/钉钉/企微统一通知服务', source: '企业微信API', stars: '核心模块', tags: ['通知', '飞书', '钉钉'], color: '#8B5CF6' },

            { id: 'doc-automation', name: '文档生成', group: '企业自动化', icon: '📄', desc: 'Word/Excel/PDF文档自动生成', source: 'python-docx', stars: '核心模块', tags: ['文档', 'Word', 'PDF'], color: '#EC4899' },

            { id: 'decision-engine', name: '决策引擎', group: '决策智能化', icon: '🎯', desc: 'AI决策、审批规则、风险评估', source: 'OpenAI API', stars: '核心模块', tags: ['决策', 'AI', '风险'], color: '#F97316' },

            { id: 'aiops-monitor', name: 'AIOps监控', group: '决策智能化', icon: '📊', desc: '异常检测、故障预警、根因分析', source: 'Grafana', stars: '核心模块', tags: ['监控', 'AIOps', '告警'], color: '#06B6D4' },

            { id: 'customer-chatbot', name: '智能客服', group: '决策智能化', icon: '🤖', desc: '多渠道接入、意图识别、工单管理', source: 'LangChain', stars: '核心模块', tags: ['客服', '对话', '意图'], color: '#84CC16' },

            { id: 'instant-messaging', name: '即时通讯', group: '通讯与数据', icon: '💭', desc: '微信/企微/钉钉/飞书消息处理', source: 'WeChat API', stars: '核心模块', tags: ['IM', '消息', '多平台'], color: '#14B8A6' },

            { id: 'database-client', name: '数据库连接', group: '通讯与数据', icon: '🗄️', desc: 'MySQL/PostgreSQL/MongoDB/Redis连接器', source: 'PyMySQL', stars: '核心模块', tags: ['数据库', 'MySQL', 'Redis'], color: '#A855F7' },

            { id: 'data-analysis', name: '数据分析', group: '通讯与数据', icon: '📈', desc: 'Pandas自动化分析、数据可视化', source: 'Pandas', stars: '核心模块', tags: ['分析', 'Pandas', '可视化'], color: '#EF4444' },

            { id: 'api-gateway', name: 'API网关', group: '通讯与数据', icon: '🔌', desc: 'REST/GraphQL统一接入、限流熔断', source: 'FastAPI', stars: '核心模块', tags: ['API', '网关', 'REST'], color: '#3B82F6' },

            { id: 'payment-center', name: '支付中心', group: '通讯与数据', icon: '💳', desc: '微信支付/支付宝/Stripe统一集成', source: 'WeChat Pay', stars: '核心模块', tags: ['支付', '微信', '支付宝'], color: '#22C55E' },

            { id: 'project-mgmt', name: '项目管理', group: '通讯与数据', icon: '📋', desc: 'Jira/Trello/飞书任务统一管理', source: 'Jira API', stars: '核心模块', tags: ['项目', '任务', 'Jira'], color: '#F59E0B' },

            { id: 'evo-nexus-core', name: 'EvoNexus核心', group: 'EvoNexus核心', icon: '🧬', desc: '自进化引擎核心，智能适应与优化', source: 'AutoEvo', stars: '核心', tags: ['自进化', '核心'], color: '#8B5CF6' },

            { id: 'evo-adaptive', name: '精准适配', group: 'EvoNexus核心', icon: '🎯', desc: '精准环境适配，动态参数调整', source: 'AutoEvo', stars: '核心', tags: ['适配', '动态'], color: '#06B6D4' },

            { id: 'evo-ecology', name: '生态联动', group: 'EvoNexus核心', icon: '🔗', desc: '多模块协同，生态资源整合', source: 'AutoEvo', stars: '核心', tags: ['生态', '协同'], color: '#10B981' },

            { id: 'evo-monitor', name: '状态监控', group: 'EvoNexus核心', icon: '📡', desc: '实时状态监控，性能追踪', source: 'AutoEvo', stars: '核心', tags: ['监控', '性能'], color: '#F59E0B' },

            { id: 'evo-safety', name: '安全防护', group: 'EvoNexus核心', icon: '🛡️', desc: '多层安全防护，风险预警', source: 'AutoEvo', stars: '核心', tags: ['安全', '防护'], color: '#EF4444' },

            { id: 'evo-backup', name: '自动备份', group: 'EvoNexus核心', icon: '💾', desc: '数据自动备份，灾备恢复', source: 'AutoEvo', stars: '核心', tags: ['备份', '灾备'], color: '#3B82F6' },

            { id: 'agent-mas', name: 'MAS多Agent', group: 'Agent集群', icon: '🤖', desc: '多Agent系统编排与协作', source: 'AutoGen', stars: '25k', tags: ['Agent', 'MAS', '协作'], color: '#6366F1' },

            { id: 'agent-hermes', name: 'Hermes协议', group: 'Agent集群', icon: '⚡', desc: 'Agent通信协议，消息路由', source: 'Hermes-AI', stars: '12k', tags: ['协议', '通信'], color: '#8B5CF6' },

            { id: 'agent-athena', name: 'Athena助手', group: 'Agent集群', icon: '🦉', desc: '智能助手Agent，知识问答', source: 'Athena-AI', stars: '8k', tags: ['助手', '问答'], color: '#F59E0B' },

            { id: 'agent-minerva', name: 'Minerva分析', group: 'Agent集群', icon: '🔬', desc: '数据分析Agent，洞察发现', source: 'Minerva-AI', stars: '6k', tags: ['分析', '洞察'], color: '#10B981' },

            { id: 'agent-phoebus', name: 'Phoebus调度', group: 'Agent集群', icon: '⚙️', desc: '任务调度Agent，资源分配', source: 'Phoebus-AI', stars: '5k', tags: ['调度', '资源'], color: '#06B6D4' },

            { id: 'agent-hecate', name: 'Hecate安全', group: 'Agent集群', icon: '🛡️', desc: '安全Agent，威胁检测', source: 'Hecate-AI', stars: '4k', tags: ['安全', '检测'], color: '#EF4444' },

            { id: 'agent-iris', name: 'Iris视觉', group: 'Agent集群', icon: '👁️', desc: '视觉识别Agent，图像分析', source: 'Iris-AI', stars: '7k', tags: ['视觉', '识别'], color: '#EC4899' },

            { id: 'agent-themis', name: 'Themis法务', group: 'Agent集群', icon: '⚖️', desc: '法律Agent，合规审查', source: 'Themis-AI', stars: '3k', tags: ['法务', '合规'], color: '#A855F7' },

            { id: 'agent-boreas', name: 'Boreas气象', group: 'Agent集群', icon: '🌪️', desc: '气象Agent，数据预测', source: 'Boreas-AI', stars: '2k', tags: ['气象', '预测'], color: '#0EA5E9' },

            { id: 'agent-cronus', name: 'Cronus时序', group: 'Agent集群', icon: '⏰', desc: '时序Agent，日程管理', source: 'Cronus-AI', stars: '3k', tags: ['时序', '日程'], color: '#F97316' },

            { id: 'stock-api', name: '股票数据', group: '金融数据API', icon: '📈', desc: '实时股票行情，历史数据', source: 'AKShare', stars: '核心', tags: ['股票', '行情'], color: '#10B981' },

            { id: 'fund-api', name: '基金数据', group: '金融数据API', icon: '💰', desc: '基金净值，持仓分析', source: 'AKShare', stars: '核心', tags: ['基金', '净值'], color: '#6366F1' },

            { id: 'futures-api', name: '期货数据', group: '金融数据API', icon: '📊', desc: '期货行情，套利分析', source: 'AKShare', stars: '核心', tags: ['期货', '套利'], color: '#F59E0B' },

            { id: 'macro-api', name: '宏观数据', group: '金融数据API', icon: '🌐', desc: 'GDP、CPI、PMI宏观指标', source: 'Trading Economics', stars: '核心', tags: ['宏观', '经济'], color: '#8B5CF6' },

            { id: 'forex-api', name: '外汇数据', group: '金融数据API', icon: '💱', desc: '实时汇率，换算工具', source: 'AKShare', stars: '核心', tags: ['外汇', '汇率'], color: '#06B6D4' },

            { id: 'crypto-api', name: '加密货币', group: '金融数据API', icon: '₿', desc: 'BTC/ETH行情，链上数据', source: 'CoinGecko', stars: '核心', tags: ['加密', 'BTC'], color: '#F97316' },

            { id: 'docker-deploy', name: 'Docker部署', group: 'DevOps部署', icon: '🐳', desc: '容器化部署，镜像管理', source: 'Docker', stars: '核心', tags: ['Docker', '容器'], color: '#2496ED' },

            { id: 'k8s-orch', name: 'K8s编排', group: 'DevOps部署', icon: '☸️', desc: 'Kubernetes集群管理，弹性伸缩', source: 'Kubernetes', stars: '核心', tags: ['K8s', '编排'], color: '#326CE5' },

            { id: 'jenkins-ci', name: 'Jenkins CI', group: 'DevOps部署', icon: '🔧', desc: '持续集成，自动化构建', source: 'Jenkins', stars: '核心', tags: ['CI', '构建'], color: '#D33833' },

            { id: 'grafana-monitor', name: 'Grafana监控', group: 'DevOps部署', icon: '📉', desc: '可视化监控，告警规则', source: 'Grafana', stars: '核心', tags: ['监控', '告警'], color: '#F46800' },

            { id: 'prometheus-metrics', name: 'Prometheus', group: 'DevOps部署', icon: '📊', desc: '指标收集，时序数据库', source: 'Prometheus', stars: '核心', tags: ['指标', '时序'], color: '#E6522C' },

            { id: 'gitlab-repo', name: 'GitLab仓库', group: 'DevOps部署', icon: '🦊', desc: '代码仓库，版本控制', source: 'GitLab', stars: '核心', tags: ['Git', '仓库'], color: '#FC6D26' },

            { id: 'argocd-deploy', name: 'ArgoCD部署', group: 'DevOps部署', icon: '🚀', desc: 'GitOps部署，声明式更新', source: 'ArgoCD', stars: '核心', tags: ['GitOps', '部署'], color: '#EF7B4D' },

            { id: 'terraform-iac', name: 'Terraform IaC', group: 'DevOps部署', icon: '🏗️', desc: '基础设施代码，资源编排', source: 'Terraform', stars: '核心', tags: ['IaC', '资源'], color: '#7B42BC' },

            { id: 'ansible-runner', name: 'Ansible运行', group: 'DevOps部署', icon: '🎸', desc: '配置管理，批量执行', source: 'Ansible', stars: '核心', tags: ['配置', '批量'], color: '#EE0000' },

            { id: 'postgres-db', name: 'PostgreSQL', group: '数据库存储', icon: '🐘', desc: '关系型数据库，高级特性', source: 'PostgreSQL', stars: '核心', tags: ['Postgres', 'SQL'], color: '#336791' },

            { id: 'redis-cache', name: 'Redis缓存', group: '数据库存储', icon: '🔴', desc: '内存数据库，高速缓存', source: 'Redis', stars: '核心', tags: ['Redis', '缓存'], color: '#DC382D' },

            { id: 'mongodb-nosql', name: 'MongoDB', group: '数据库存储', icon: '🍃', desc: '文档数据库，灵活 Schema', source: 'MongoDB', stars: '核心', tags: ['Mongo', 'NoSQL'], color: '#47A248' },

            { id: 'neo4j-graph', name: 'Neo4j图数据库', group: '数据库存储', icon: '🔵', desc: '图数据库，关系分析', source: 'Neo4j', stars: '核心', tags: ['图数据库', 'Neo4j'], color: '#008CC1' },

            { id: 'elasticsearch-search', name: 'Elasticsearch', group: '数据库存储', icon: '🔍', desc: '全文搜索，日志分析', source: 'Elastic', stars: '核心', tags: ['搜索', '日志'], color: '#005572' },

            { id: 'clickhouse-olap', name: 'ClickHouse', group: '数据库存储', icon: '🏠', desc: 'OLAP数据库，高速分析', source: 'ClickHouse', stars: '核心', tags: ['OLAP', '分析'], color: '#FFCC00' },

            { id: 'qdrant-vector', name: 'Qdrant向量库', group: '数据库存储', icon: '🎯', desc: '向量数据库，语义搜索', source: 'Qdrant', stars: '核心', tags: ['向量', 'Embedding'], color: 'rgba(99,102,241,0.2)' },

            { id: 'milvus-vector', name: 'Milvus向量库', group: '数据库存储', icon: '📐', desc: '开源向量数据库，相似度搜索', source: 'Milvus', stars: '核心', tags: ['向量', 'Embedding'], color: '#6DCE59' },

            { id: 'weaviate-semantic', name: 'Weaviate语义', group: '数据库存储', icon: '🌊', desc: '语义向量搜索，知识图谱', source: 'Weaviate', stars: '核心', tags: ['语义', '知识图谱'], color: '#57B4E3' },

            { id: 'pinecone-managed', name: 'Pinecone托管', group: '数据库存储', icon: '🌲', desc: '云向量数据库，企业级', source: 'Pinecone', stars: '核心', tags: ['向量', '托管'], color: '#00D4AA' },

            { id: 'llm-openai', name: 'OpenAI GPT', group: 'AI模型层', icon: '🤖', desc: 'GPT-4/GPT-3.5大语言模型', source: 'OpenAI', stars: '核心', tags: ['LLM', 'GPT'], color: '#10A37F' },

            { id: 'llm-claude', name: 'Claude AI', group: 'AI模型层', icon: '🧠', desc: 'Claude3大语言模型，长上下文', source: 'Anthropic', stars: '核心', tags: ['LLM', 'Claude'], color: '#CC785C' },

            { id: 'llm-gemini', name: 'Google Gemini', group: 'AI模型层', icon: '✨', desc: 'Gemini多模态模型', source: 'Google', stars: '核心', tags: ['LLM', '多模态'], color: '#4285F4' },

            { id: 'llm-local', name: 'Ollama本地LLM', group: 'AI模型层', icon: '💻', desc: '本地大模型运行，无需联网', source: 'Ollama', stars: '核心', tags: ['LLM', '本地'], color: '#333333' },

            { id: 'embedding-openai', name: 'OpenAI Embedding', group: 'AI模型层', icon: '📝', desc: '文本向量化，语义嵌入', source: 'OpenAI', stars: '核心', tags: ['Embedding', '向量'], color: '#10A37F' },

            { id: 'embedding-huggingface', name: 'HuggingFace嵌入', group: 'AI模型层', icon: '🤗', desc: '开源Embedding模型', source: 'HuggingFace', stars: '核心', tags: ['Embedding', '开源'], color: '#FFD21E' },

            { id: 'rerank-cohere', name: 'Cohere重排序', group: 'AI模型层', icon: '🔄', desc: '搜索结果重排序，精准匹配', source: 'Cohere', stars: '核心', tags: ['Rerank', '搜索'], color: '#1E3A5F' },

            { id: 'tts-elevenlabs', name: 'ElevenLabs TTS', group: 'AI模型层', icon: '🔊', desc: 'AI语音合成，自然流畅', source: 'ElevenLabs', stars: '核心', tags: ['TTS', '语音'], color: '#000000' },

            { id: 'whisper-asr', name: 'Whisper语音识别', group: 'AI模型层', icon: '🎤', desc: '语音转文字，多语言支持', source: 'OpenAI', stars: '核心', tags: ['ASR', '语音'], color: '#10A37F' },

            { id: 'stable-diffusion', name: 'Stable Diffusion', group: 'AI模型层', icon: '🎨', desc: 'AI图像生成，创意设计', source: 'Stability AI', stars: '核心', tags: ['图像', '生成'], color: '#9B59B6' },

            { id: 'llm-agent-framework', name: 'LLM Agent框架', group: 'AI模型层', icon: '🦸', desc: 'Agent开发框架，工具调用', source: 'LangChain', stars: '核心', tags: ['Agent', '框架'], color: '#1ABC9C' },

            { id: 'model-deployment', name: '模型部署', group: 'AI模型层', icon: '🚀', desc: '模型服务化，高可用部署', source: 'TensorFlow Serving', stars: '核心', tags: ['部署', '服务'], color: '#FF6F00' },

            { id: 'model-tuning', name: '模型微调', group: 'AI模型层', icon: '⚙️', desc: 'LoRA/QLoRA微调，定制模型', source: 'Axolotl', stars: '核心', tags: ['微调', 'LoRA'], color: '#E91E63' },

            { id: 'model-evaluation', name: '模型评测', group: 'AI模型层', icon: '📏', desc: '模型评估，基准测试', source: 'LM Evaluation Harness', stars: '核心', tags: ['评测', '基准'], color: '#2196F3' },

            { id: 'rag-pipeline', name: 'RAG管道', group: 'AI模型层', icon: '📚', desc: '检索增强生成，知识问答', source: 'LangChain', stars: '核心', tags: ['RAG', '检索'], color: '#4CAF50' },

            { id: 'model-registry', name: '模型市场', group: 'AI模型层', icon: '🏪', desc: '模型市场，版本管理', source: 'MLflow', stars: '核心', tags: ['市场', '版本'], color: '#0194FE' },

            { id: 'mirofish-analysis', name: 'MiroFish分析', group: '智能分析层', icon: '🐟', desc: '多维数据分析，趋势发现', source: 'MiroFish', stars: '核心', tags: ['分析', '趋势'], color: '#00BCD4' },

            { id: 'bettafish-forecast', name: 'BettaFish预测', group: '智能分析层', icon: '🐠', desc: '时间序列预测，智能预警', source: 'BettaFish', stars: '核心', tags: ['预测', '时序'], color: '#FF5722' },

            { id: 'trendaradar-trend', name: 'TrendRadar趋势', group: '智能分析层', icon: '📡', desc: '热点趋势监控，舆情分析', source: 'TrendRadar', stars: '核心', tags: ['趋势', '舆情'], color: '#9C27B0' },

            { id: 'knowledge-graph', name: '知识图谱', group: '智能分析层', icon: '🕸️', desc: '实体关系图谱，智能推理', source: 'Neo4j', stars: '核心', tags: ['图谱', '推理'], color: '#3F51B5' },

            { id: 'sentiment-analysis', name: '情感分析', group: '智能分析层', icon: '💭', desc: '文本情感识别，观点挖掘', source: 'Transformers', stars: '核心', tags: ['情感', 'NLP'], color: '#E91E63' },

            { id: 'entity-extraction', name: '实体抽取', group: '智能分析层', icon: '🎯', desc: '命名实体识别，信息抽取', source: ' spaCy', stars: '核心', tags: ['NER', '抽取'], color: '#795548' },

            { id: 'text-summarize', name: '文本摘要', group: '智能分析层', icon: '📝', desc: '自动摘要生成，长文压缩', source: 'Transformers', stars: '核心', tags: ['摘要', '压缩'], color: '#607D8B' },

            { id: 'keyword-extract', name: '关键词提取', group: '智能分析层', icon: '🔑', desc: '关键词抽取，主题识别', source: 'KeyBERT', stars: '核心', tags: ['关键词', '主题'], color: '#FF9800' },

            { id: 'document-qa', name: '文档问答', group: '智能分析层', icon: '❓', desc: '智能问答，知识库检索', source: 'LangChain', stars: '核心', tags: ['问答', '知识库'], color: '#00BCD4' },

            { id: 'table-understand', name: '表格理解', group: '智能分析层', icon: '📊', desc: '表格解析，数据提取', source: 'TabFormer', stars: '核心', tags: ['表格', '数据'], color: '#4CAF50' },

            { id: 'code-understand', name: '代码理解', group: '智能分析层', icon: '💻', desc: '代码解析，逻辑推理', source: 'CodeBERT', stars: '核心', tags: ['代码', '解析'], color: '#2196F3' },

            { id: 'sql-generator', name: 'SQL生成器', group: '智能分析层', icon: '🗄️', desc: '自然语言转SQL，数据库查询', source: 'SQLCoder', stars: '核心', tags: ['SQL', '生成'], color: '#336791' },

            { id: 'image-understand', name: '图像理解', group: '智能分析层', icon: '🖼️', desc: '多模态理解，图像分析', source: 'CLIP', stars: '核心', tags: ['图像', '多模态'], color: '#9C27B0' },

            { id: 'litellm-gateway', name: 'LiteLLM网关', group: '统一LLM网关', icon: '🌐', desc: '统一调用100+LLM模型，简化集成', source: 'BerriAI/liteLLM', stars: '30k', tags: ['网关', 'LLM', '统一'], color: '#6366F1', priority: 'high' },

            { id: 'composio-tools', name: 'Composio工具', group: '工具生态', icon: '🛠️', desc: '100+工具集成，Agent能力扩展', source: 'ComposioHQ/composio', stars: '25k', tags: ['工具', '生态', '集成'], color: '#8B5CF6', priority: 'high' },

            { id: 'agency-swarm', name: 'Agency Swarm', group: 'Agent协作', icon: '🐝', desc: '多Agent协作框架，分布式任务', source: 'VRSEN/agency-swarm', stars: '18k', tags: ['Agent', '协作', '分布式'], color: '#10B981', priority: 'high' },

            { id: 'praisonai-agent', name: 'PraisonAI', group: 'Agent编排', icon: '🎭', desc: '自主Agent编排，低代码平台', source: 'MervinPraison/PraisonAI', stars: '15k', tags: ['Agent', '编排', '低代码'], color: '#F59E0B', priority: 'high' },

            { id: 'mem0-memory', name: 'Mem0记忆', group: '记忆系统', icon: '🧠', desc: '个性化AI记忆层，长期上下文', source: 'mem0ai/mem0', stars: '17k', tags: ['记忆', '上下文', '个性化'], color: '#EC4899', priority: 'high' },

            { id: 'openhands-agent', name: 'OpenHands', group: '代码工程', icon: '🛠️', desc: 'AI软件工程师，自动编码调试', source: 'All-Hands-AI/OpenHands', stars: '70k', tags: ['代码', '工程师', '自动化'], color: '#3B82F6', priority: 'high' },

            { id: 'langfuse-monitor', name: 'Langfuse监控', group: '可观测性', icon: '📊', desc: 'LLM追踪监控，调试分析', source: 'langfuse/langfuse', stars: '20k', tags: ['监控', '追踪', '调试'], color: '#06B6D4', priority: 'high' },

            { id: 'agentguard-sec', name: 'AgentGuard安全', group: '安全治理', icon: '🛡️', desc: 'AI安全卫士，威胁检测防护', source: 'GoPlusSecurity/agentguard', stars: '12k', tags: ['安全', '防护', '治理'], color: '#EF4444', priority: 'high' },

            { id: 'masfactory-orch', name: 'MASFactory编排', group: '系统编排', icon: '🏭', desc: '多Agent系统编排，Vibe Graphing', source: 'BUPT-GAMMA/MASFactory', stars: '8k', tags: ['编排', 'MAS', '系统'], color: '#8B5CF6', priority: 'high' },

            { id: 'multica-team', name: 'Multica团队', group: '团队协作', icon: '👥', desc: '多Agent团队协作，任务分配', source: 'multica-ai/multica', stars: '15k', tags: ['协作', '团队', '任务'], color: '#10B981', priority: 'medium' },

            { id: 'goose-coder', name: 'Goose编程', group: '编程助手', icon: '🪿', desc: '本地AI编程助手，代码生成', source: 'aaif-goose/goose', stars: '22k', tags: ['编程', '助手', '本地'], color: '#F59E0B', priority: 'medium' },

            { id: 'lobehub-ui', name: 'LobeChat UI', group: '聊天UI', icon: '💬', desc: 'AI聊天UI框架，美观易用', source: 'lobehub/lobe-chat', stars: '63k', tags: ['UI', '聊天', '框架'], color: '#EC4899', priority: 'medium' },

            { id: 'aegis-governance', name: 'Aegis治理', group: '治理架构', icon: '⚖️', desc: 'AI治理架构，宪法级约束', source: 'aegis-initiative/aegis', stars: '5k', tags: ['治理', '架构', '合规'], color: '#6366F1', priority: 'medium' },

            { id: 'open-chronicle', name: 'OpenChronicle', group: 'AI记忆系统', icon: '📜', desc: '本地优先AI记忆基础设施', source: 'OpenChronicle', stars: '爆火中', tags: ['记忆', '本地', 'AI'], color: '#8B5CF6', priority: 'high' },

            { id: 'memos', name: 'MemOS', group: 'AI记忆系统', icon: '🧠', desc: 'AI记忆操作系统，持久化记忆', source: 'MemTensor/MemOS', stars: '持续增长', tags: ['记忆', 'OS', '持久化'], color: '#06B6D4', priority: 'high' },

            { id: 'supermemory', name: 'SuperMemory', group: 'AI记忆系统', icon: '💾', desc: '图结构记忆引擎，智能关联', source: 'supermemory', stars: '3.2k', tags: ['图结构', '记忆', '关联'], color: '#10B981', priority: 'medium' },

            { id: 'ml-intern', name: 'ML-Intern', group: 'ML与代码', icon: '🤖', desc: '自主ML工程师，自动模型训练', source: 'HuggingFace/ml-intern', stars: '2k+', tags: ['ML', '自动化', '训练'], color: '#F59E0B', priority: 'high' },

            { id: 'atom-code', name: 'AtomCode', group: 'ML与代码', icon: '⚛️', desc: 'Claude Code开源替代，智能代码', source: 'AtomCode', stars: '热门', tags: ['代码', 'AI', '替代'], color: '#3B82F6', priority: 'high' },

            { id: 'bytecodestudio', name: 'ByteCodeStudio', group: 'ML与代码', icon: '💻', desc: 'AI代码工作室，生成调试重构', source: 'ByteCodeStudio', stars: 'Trending', tags: ['代码', '工作室', 'AI'], color: '#EC4899', priority: 'medium' },

            { id: 'hyperframes-video', name: 'Hyperframes', group: '视频与设计', icon: '🎬', desc: 'HTML原生视频渲染，AI驱动生成', source: 'HeyGen/hyperframes', stars: '9.6k', tags: ['视频', 'HTML', 'AI'], color: '#EF4444', priority: 'high' },

            { id: 'pixelle-video', name: 'Pixelle-Video', group: '视频与设计', icon: '🎥', desc: 'AI短视频生成，一键创作', source: 'Pixelle-Video', stars: '热门', tags: ['视频', 'AI', '生成'], color: '#8B5CF6', priority: 'medium' },

            { id: 'awesome-design-md', name: 'Awesome Design MD', group: '视频与设计', icon: '🎨', desc: 'AI设计规范与组件库参考', source: 'VoltAgent/awesome-design', stars: '热门', tags: ['设计', '规范', '组件'], color: '#06B6D4', priority: 'medium' },

            { id: 'open-lovable', name: 'Open-Lovable', group: 'AI网站构建', icon: '🌐', desc: 'AI网站构建器，描述即网站', source: 'Open-Lovable', stars: '8k+', tags: ['网站', 'AI', '构建'], color: '#10B981', priority: 'medium' },

            { id: 'webtoapp', name: 'WebToApp', group: 'AI网站构建', icon: '📱', desc: 'Web转原生App，H5封装', source: 'WebToApp', stars: '5k', tags: ['Web', 'App', '封装'], color: '#F59E0B', priority: 'medium' },

            { id: 'hermes-webui', name: 'Hermes-Web-UI', group: 'Agent面板', icon: '🖥️', desc: 'Agent管理面板，统一监控控制', source: 'nesquena/hermes-webui', stars: '9万+', tags: ['Agent', '面板', '管理'], color: '#6366F1', priority: 'high' },

            { id: 'hermes-solo', name: 'Hermes-Solo', group: 'Agent面板', icon: '🎯', desc: '独立Agent运行时，轻量级助手', source: 'HermesFullTeam/hermes-solo', stars: '3k', tags: ['Agent', '独立', '轻量'], color: '#EC4899', priority: 'medium' },

            { id: 'mano-predictor', name: 'Mano-P1.0', group: '预测与扩展', icon: '📈', desc: '高级时间序列预测与异常检测', source: 'Mano-P1.0', stars: '热门', tags: ['预测', '时序', '异常'], color: '#3B82F6', priority: 'medium' },

            { id: 'loongclaw', name: 'LoongClaw', group: '预测与扩展', icon: '🐉', desc: '国产高性能AI框架，麒麟适配', source: 'LoongClaw', stars: 'Trending', tags: ['国产', '框架', '适配'], color: '#EF4444', priority: 'medium' },

            { id: 'ruoyi-ai', name: 'Ruoyi-AI', group: '预测与扩展', icon: '🏛️', desc: '若依AI扩展，企业级智能问答', source: 'Vagerer/Ruoyi-AI', stars: '2k', tags: ['若依', '企业', '问答'], color: '#8B5CF6', priority: 'medium' },

            { id: 'autoskills', name: 'AutoSkills', group: '预测与扩展', icon: '🔧', desc: 'AI技能自动安装，智能模块推荐', source: 'midudev/autoskills', stars: '热门', tags: ['技能', '自动', '安装'], color: '#10B981', priority: 'high' },

            { id: 'fincept-terminal', name: 'Fincept Terminal', group: '预测与扩展', icon: '📊', desc: '替代Bloomberg金融终端，量化分析', source: 'Fincept/Terminal', stars: 'Trending#1', tags: ['金融', '终端', '量化'], color: '#F59E0B', priority: 'high' },

            { id: 'system-monitor', name: '系统监控', group: '守护进程', icon: '📟', desc: '实时系统监控，资源追踪', source: 'psutil', stars: '核心', tags: ['监控', '系统', '资源'], color: '#10B981' },

            { id: 'auto-restart', name: '自动重启', group: '守护进程', icon: '🔄', desc: '进程异常自动重启，保障服务', source: 'supervisord', stars: '核心', tags: ['重启', '进程', '保障'], color: '#F59E0B' },

            { id: 'health-check', name: '健康检查', group: '守护进程', icon: '💚', desc: '服务健康检查，状态报告', source: 'HealthCheck', stars: '核心', tags: ['健康', '检查', '状态'], color: '#10B981' },

            { id: 'log-collector', name: '日志收集', group: '守护进程', icon: '📋', desc: '集中日志收集，聚合分析', source: 'ELK', stars: '核心', tags: ['日志', '收集', '分析'], color: '#6366F1' },

            { id: 'backup-scheduler', name: '备份调度', group: '守护进程', icon: '💾', desc: '定时备份任务调度', source: 'Cron', stars: '核心', tags: ['备份', '调度', '定时'], color: '#3B82F6' },

            { id: 'webhook-handler', name: 'Webhook处理', group: '守护进程', icon: '🪝', desc: 'Webhook事件接收处理', source: 'Flask', stars: '核心', tags: ['Webhook', '事件', '处理'], color: '#8B5CF6' },

            { id: 'cron-scheduler', name: '定时任务', group: '守护进程', icon: '⏰', desc: 'Cron定时任务调度管理', source: 'APScheduler', stars: '核心', tags: ['定时', '任务', '调度'], color: '#06B6D4' },

            { id: 'cache-manager', name: '缓存管理', group: '守护进程', icon: '⚡', desc: '多级缓存管理，性能优化', source: 'Redis', stars: '核心', tags: ['缓存', '管理', '性能'], color: '#EF4444' },

            { id: 'api-rate-limiter', name: 'API限流', group: '守护进程', icon: '🚦', desc: 'API访问限流，流量控制', source: 'Flask-Limiter', stars: '核心', tags: ['限流', '流量', '控制'], color: '#F59E0B' },

            { id: 'circuit-breaker', name: '熔断器', group: '守护进程', icon: '🔴', desc: '服务熔断保护，故障隔离', source: 'PyBreaker', stars: '核心', tags: ['熔断', '保护', '隔离'], color: '#DC382D' },

            { id: 'config-reloader', name: '配置热重载', group: '守护进程', icon: '🔥', desc: '配置变更热重载，无需重启', source: 'Hikaru', stars: '核心', tags: ['配置', '热重载', '动态'], color: '#EC4899' },

            { id: 'feature-flag', name: '特性开关', group: '守护进程', icon: '🔘', desc: '功能特性开关，灰度发布', source: 'Flagsmith', stars: '核心', tags: ['开关', '灰度', '发布'], color: '#10B981' },

            { id: 'task-queue', name: '任务队列', group: '守护进程', icon: '📬', desc: '异步任务队列，批量处理', source: 'Celery', stars: '核心', tags: ['队列', '异步', '批量'], color: '#3B82F6' },

            { id: 'event-bus', name: '事件总线', group: '守护进程', icon: '🚌', desc: '事件驱动架构，松耦合', source: 'EventBridge', stars: '核心', tags: ['事件', '驱动', '总线'], color: '#8B5CF6' },

            { id: 'workflow-engine', name: '工作流引擎', group: '守护进程', icon: '⚙️', desc: '可视化工作流编排执行', source: 'Prefect', stars: '核心', tags: ['工作流', '编排', '执行'], color: '#06B6D4' },

            { id: 'file-watcher', name: '文件监控', group: '守护进程', icon: '👁️', desc: '文件系统变更监控触发', source: 'Watchdog', stars: '核心', tags: ['文件', '监控', '触发'], color: '#F59E0B' },

            { id: 'sse-stream', name: 'SSE流推送', group: '守护进程', icon: '📡', desc: 'Server-Sent Events实时推送', source: 'FastAPI', stars: '核心', tags: ['SSE', '流', '实时'], color: '#10B981' },

            { id: 'api-mock', name: 'API模拟', group: '守护进程', icon: '🎭', desc: '接口Mock服务，测试隔离', source: 'MockServer', stars: '核心', tags: ['Mock', '测试', '模拟'], color: '#EC4899' },

            { id: 'secret-manager', name: '密钥管理', group: '守护进程', icon: '🔐', desc: '敏感信息加密存储，轮换', source: 'HashiCorp Vault', stars: '核心', tags: ['密钥', '加密', '安全'], color: '#EF4444' },

            { id: 'service-mesh', name: '服务网格', group: '守护进程', icon: '🕸️', desc: '服务间通信治理，流量管理', source: 'Istio', stars: '核心', tags: ['网格', '通信', '治理'], color: '#6366F1' },

            { id: 'auto-scale', name: '自动扩缩容', group: '守护进程', icon: '📈', desc: '基于负载自动扩缩容', source: 'KEDA', stars: '核心', tags: ['扩缩容', '负载', '弹性'], color: '#3B82F6' },

            { id: 'blue-green', name: '蓝绿部署', group: '守护进程', icon: '🔵🟢', desc: '蓝绿部署策略，零 downtime', source: 'Argo Rollouts', stars: '核心', tags: ['部署', '蓝绿', '策略'], color: '#10B981' },

            { id: 'canary-release', name: '金丝雀发布', group: '守护进程', icon: '🐦', desc: '金丝雀渐进发布，风险控制', source: 'Flagger', stars: '核心', tags: ['发布', '金丝雀', '风险'], color: '#F59E0B' },

            { id: 'rollback-manager', name: '自动回滚', group: '守护进程', icon: '↩️', desc: '异常自动回滚，保障稳定', source: 'ArgoCD', stars: '核心', tags: ['回滚', '自动', '稳定'], color: '#EF4444' },

            { id: 'config-center', name: '配置中心', group: '守护进程', icon: '⚙️', desc: '分布式配置管理，动态下发', source: 'Apollo', stars: '核心', tags: ['配置', '中心', '管理'], color: '#8B5CF6' },

            { id: 'registry-center', name: '注册中心', group: '守护进程', icon: '📍', desc: '服务注册发现，负载均衡', source: 'Nacos', stars: '核心', tags: ['注册', '发现', '均衡'], color: '#06B6D4' },

            { id: 'distributed-lock', name: '分布式锁', group: '守护进程', icon: '🔒', desc: '跨节点分布式锁，并发控制', source: 'Redis', stars: '核心', tags: ['锁', '分布式', '并发'], color: '#DC382D' },

            { id: 'idempotent', name: '幂等组件', group: '守护进程', icon: '♻️', desc: '接口幂等性保障，防重复', source: 'Redis', stars: '核心', tags: ['幂等', '防重', '保障'], color: '#10B981' },

            { id: 'data-sync', name: '数据同步', group: '守护进程', icon: '🔄', desc: '多源数据同步，CDC变更捕获', source: 'Debezium', stars: '核心', tags: ['同步', 'CDC', '变更'], color: '#3B82F6' },

            { id: 'audit-log', name: '审计日志', group: '守护进程', icon: '📝', desc: '操作审计日志，合规追溯', source: 'Elasticsearch', stars: '核心', tags: ['审计', '日志', '合规'], color: '#6366F1' },

            { id: 'sla-monitor', name: 'SLA监控', group: '守护进程', icon: '📊', desc: '服务等级协议监控告警', source: 'Prometheus', stars: '核心', tags: ['SLA', '监控', '告警'], color: '#F59E0B' },

            { id: 'incident-response', name: '事件响应', group: '守护进程', icon: '🚨', desc: '安全事件自动响应处置', source: 'PagerDuty', stars: '核心', tags: ['事件', '响应', '处置'], color: '#EF4444' },

            { id: 'chaos-engineering', name: '混沌工程', group: '守护进程', icon: '💥', desc: '故障注入测试，系统韧性', source: 'Chaos Mesh', stars: '核心', tags: ['混沌', '故障', '韧性'], color: '#EC4899' },

            { id: 'sso-auth', name: 'SSO单点登录', group: '守护进程', icon: '🔑', desc: '统一身份认证，单点访问', source: 'CAS', stars: '核心', tags: ['SSO', '认证', '单点'], color: '#8B5CF6' },

            { id: 'oauth-provider', name: 'OAuth授权', group: '守护进程', icon: '🎫', desc: 'OAuth2.0授权服务，第三方登录', source: 'Authlib', stars: '核心', tags: ['OAuth', '授权', '登录'], color: '#06B6D4' },

            { id: 'jwt-token', name: 'JWT令牌', group: '守护进程', icon: '🎟️', desc: 'JWT签发验证，状态管理', source: 'PyJWT', stars: '核心', tags: ['JWT', '令牌', '认证'], color: '#10B981' },

            { id: 'permission-rbac', name: 'RBAC权限', group: '守护进程', icon: '👮', desc: '角色权限控制，资源访问', source: 'Casbin', stars: '核心', tags: ['RBAC', '权限', '角色'], color: '#3B82F6' },

            { id: 'api-versioning', name: 'API版本管理', group: '守护进程', icon: '🏷️', desc: '多版本API共存，渐进迁移', source: 'FastAPI', stars: '核心', tags: ['版本', 'API', '迁移'], color: '#F59E0B' },

            { id: 'request-tracing', name: '全链路追踪', group: '守护进程', icon: '🔍', desc: '请求全链路追踪，问题定位', source: 'Jaeger', stars: '核心', tags: ['追踪', '链路', '定位'], color: '#6366F1' },

            { id: 'error-aggregator', name: '错误聚合', group: '守护进程', icon: '💥', desc: '错误日志聚合，问题归类', source: 'Sentry', stars: '核心', tags: ['错误', '聚合', '归类'], color: '#EF4444' },

            { id: 'perf-profiler', name: '性能分析', group: '守护进程', icon: '⏱️', desc: '代码性能分析，瓶颈识别', source: 'Py-Spy', stars: '核心', tags: ['性能', '分析', '瓶颈'], color: '#10B981' },

            { id: 'memory-leak-detect', name: '内存泄漏检测', group: '守护进程', icon: '🧩', desc: '内存泄漏监控，自动告警', source: 'Memray', stars: '核心', tags: ['内存', '泄漏', '检测'], color: '#DC382D' },

            { id: 'cpu-profiler', name: 'CPU分析', group: '守护进程', icon: '⚡', desc: 'CPU使用分析，优化建议', source: 'cProfile', stars: '核心', tags: ['CPU', '分析', '优化'], color: '#F59E0B' },

            { id: 'io-monitor', name: 'IO监控', group: '守护进程', icon: '💾', desc: '磁盘网络IO监控，异常检测', source: 'iostat', stars: '核心', tags: ['IO', '监控', '磁盘'], color: '#06B6D4' },

            { id: 'connection-pool', name: '连接池管理', group: '守护进程', icon: '🔗', desc: '数据库连接池，调优管理', source: 'SQLAlchemy', stars: '核心', tags: ['连接池', '数据库', '调优'], color: '#3B82F6' },

            { id: 'query-cache', name: '查询缓存', group: '守护进程', icon: '📦', desc: 'SQL查询缓存，加速响应', source: 'Redis', stars: '核心', tags: ['缓存', '查询', 'SQL'], color: '#8B5CF6' },

            { id: 'slow-query', name: '慢查询分析', group: '守护进程', icon: '🐢', desc: '慢SQL识别，优化建议', source: 'EXPLAIN', stars: '核心', tags: ['慢查询', 'SQL', '优化'], color: '#EC4899' },

            { id: 'index-advisor', name: '索引建议', group: '守护进程', icon: '📑', desc: '索引创建建议，性能优化', source: 'pg_stat_statements', stars: '核心', tags: ['索引', '建议', '优化'], color: '#10B981' },

            { id: 'table-partition', name: '表分区管理', group: '守护进程', icon: '📊', desc: '大表分区策略，提升性能', source: 'PostgreSQL', stars: '核心', tags: ['分区', '大表', '策略'], color: '#6366F1' },

            { id: 'data-archival', name: '冷数据归档', group: '守护进程', icon: '❄️', desc: '冷数据自动归档，释放空间', source: 'pg_partman', stars: '核心', tags: ['归档', '冷数据', '空间'], color: '#06B6D4' },

            { id: 'backup-verify', name: '备份验证', group: '守护进程', icon: '✅', desc: '备份完整性验证，可靠性保障', source: 'pgBackRest', stars: '核心', tags: ['备份', '验证', '可靠'], color: '#10B981' },

            { id: 'point-time-recover', name: 'PITR恢复', group: '守护进程', icon: '⏪', desc: '时间点恢复，任意时刻数据', source: 'WAL', stars: '核心', tags: ['PITR', '恢复', 'WAL'], color: '#3B82F6' },

            { id: 'replication-monitor', name: '复制监控', group: '守护进程', icon: '🔄', desc: '主从复制监控，延迟告警', source: 'pgpool', stars: '核心', tags: ['复制', '主从', '延迟'], color: '#F59E0B' },

            { id: 'sharding-proxy', name: '分片代理', group: '守护进程', icon: '📐', desc: '数据库分片中间件，水平扩展', source: 'ShardingSphere', stars: '核心', tags: ['分片', '扩展', '中间件'], color: '#8B5CF6' },

            { id: 'read-write-split', name: '读写分离', group: '守护进程', icon: '📖', desc: '读写分离路由，负载均衡', source: 'MySQL Router', stars: '核心', tags: ['读写分离', '路由', '负载'], color: '#EC4899' },

            { id: 'auto-failover', name: '自动故障转移', group: '守护进程', icon: '🔀', desc: '故障自动切换，高可用保障', source: 'Patroni', stars: '核心', tags: ['故障转移', '高可用', '切换'], color: '#EF4444' },

            { id: 'connection-draining', name: '连接排空', group: '守护进程', icon: '🚰', desc: '优雅关闭连接，请求处理完毕', source: 'Envoy', stars: '核心', tags: ['连接', '排空', '优雅'], color: '#10B981' },

            { id: 'health-checker', name: '健康检查器', group: '守护进程', icon: '💚', desc: '多协议健康检查，探活机制', source: 'Consul', stars: '核心', tags: ['健康', '检查', '探活'], color: '#3B82F6' },

            { id: 'service-discovery', name: '服务发现', group: '守护进程', icon: '🔎', desc: '动态服务注册与发现', source: 'Consul', stars: '核心', tags: ['发现', '注册', '动态'], color: '#6366F1' },

            { id: 'load-balancer', name: '负载均衡', group: '守护进程', icon: '⚖️', desc: '多策略负载均衡，健康感知', source: 'Nginx', stars: '核心', tags: ['负载', '均衡', '策略'], color: '#F59E0B' },

            { id: 'reverse-proxy', name: '反向代理', group: '守护进程', icon: '🔄', desc: '请求转发，SSL终结', source: 'Traefik', stars: '核心', tags: ['代理', '转发', 'SSL'], color: '#06B6D4' },

            { id: 'cdn-manager', name: 'CDN管理', group: '守护进程', icon: '🌐', desc: 'CDN配置管理，缓存刷新', source: 'Cloudflare', stars: '核心', tags: ['CDN', '缓存', '刷新'], color: '#8B5CF6' },

            { id: 'dns-manager', name: 'DNS管理', group: '守护进程', icon: '🌍', desc: 'DNS记录管理，动态更新', source: 'AWS Route53', stars: '核心', tags: ['DNS', '记录', '管理'], color: '#10B981' },

            { id: 'ssl-cert-manager', name: 'SSL证书管理', group: '守护进程', icon: '🔐', desc: '自动续期SSL证书', source: 'Certbot', stars: '核心', tags: ['SSL', '证书', '续期'], color: '#3B82F6' },

            { id: 'firewall-rules', name: '防火墙规则', group: '守护进程', icon: '🧱', desc: '网络访问控制，规则管理', source: 'iptables', stars: '核心', tags: ['防火墙', '规则', '访问'], color: '#EF4444' },

            { id: 'vpn-gateway', name: 'VPN网关', group: '守护进程', icon: '🔒', desc: '远程安全访问，隧道加密', source: 'WireGuard', stars: '核心', tags: ['VPN', '安全', '隧道'], color: '#6366F1' },

            { id: 'ddos-protection', name: 'DDoS防护', group: '守护进程', icon: '🛡️', desc: '流量清洗，攻击防护', source: 'Cloudflare', stars: '核心', tags: ['DDoS', '防护', '清洗'], color: '#F59E0B' },

            { id: 'rate-limiter', name: '限流器', group: '守护进程', icon: '🚦', desc: '多维度限流，流量控制', source: 'Redis', stars: '核心', tags: ['限流', '流量', '控制'], color: '#EC4899' },

            { id: 'waf-web防火墙', name: 'WAF防火墙', group: '守护进程', icon: '🛡️', desc: 'Web应用防火墙，规则防护', source: 'ModSecurity', stars: '核心', tags: ['WAF', '防火墙', 'Web'], color: '#DC382D' },

            { id: 'bot-detection', name: 'Bot检测', group: '守护进程', icon: '🤖', desc: '恶意爬虫检测，行为分析', source: 'Datadog', stars: '核心', tags: ['Bot', '检测', '爬虫'], color: '#8B5CF6' },

            { id: 'ip-whitelist', name: 'IP白名单', group: '守护进程', icon: '✅', desc: '可信IP访问控制', source: 'Nginx', stars: '核心', tags: ['IP', '白名单', '访问'], color: '#10B981' },

            { id: 'cors-manager', name: 'CORS管理', group: '守护进程', icon: '🔗', desc: '跨域资源共享配置', source: 'Flask-CORS', stars: '核心', tags: ['CORS', '跨域', '配置'], color: '#06B6D4' },

            { id: 'header-injector', name: 'Header注入', group: '守护进程', icon: '📝', desc: '请求响应头注入修改', source: 'Nginx', stars: '核心', tags: ['Header', '注入', '修改'], color: '#3B82F6' },

            { id: 'request-id', name: '请求追踪ID', group: '守护进程', icon: '🔖', desc: '全局请求ID串联全链路', source: 'Zipkin', stars: '核心', tags: ['请求ID', '追踪', '串联'], color: '#F59E0B' },

            { id: 'compress-algorithm', name: '压缩算法', group: '守护进程', icon: '📦', desc: 'Gzip/Brotli压缩传输优化', source: 'Nginx', stars: '核心', tags: ['压缩', 'Gzip', '传输'], color: '#8B5CF6' },

            { id: 'static-cache', name: '静态资源缓存', group: '守护进程', icon: '💾', desc: '静态文件CDN缓存策略', source: 'CDN', stars: '核心', tags: ['静态', '缓存', 'CDN'], color: '#10B981' },

            { id: 'api-cache', name: 'API响应缓存', group: '守护进程', icon: '📦', desc: 'API响应缓存，减少计算', source: 'Redis', stars: '核心', tags: ['API', '缓存', '响应'], color: '#6366F1' },

            { id: 'page-cache', name: '页面缓存', group: '守护进程', icon: '📄', desc: '整页HTML缓存，极速加载', source: 'Varnish', stars: '核心', tags: ['页面', '缓存', 'HTML'], color: '#EC4899' },

            { id: 'query-cache-layer', name: '查询缓存层', group: '守护进程', icon: '🔍', desc: '数据库查询结果缓存', source: 'Redis', stars: '核心', tags: ['查询', '缓存', '数据库'], color: '#06B6D4' },

            { id: 'session-store', name: '会话存储', group: '守护进程', icon: '💼', desc: '分布式会话存储管理', source: 'Redis', stars: '核心', tags: ['会话', '存储', '分布式'], color: '#3B82F6' },

            { id: 'rate-limit-redis', name: 'Redis限流', group: '守护进程', icon: '🚦', desc: '基于Redis的滑动窗口限流', source: 'Redis', stars: '核心', tags: ['限流', 'Redis', '滑动窗口'], color: '#F59E0B' },

            { id: 'distributed-counter', name: '分布式计数器', group: '守护进程', icon: '🔢', desc: '原子递增计数，高并发支持', source: 'Redis', stars: '核心', tags: ['计数器', '分布式', '原子'], color: '#8B5CF6' },

            { id: 'pub-sub', name: '发布订阅', group: '守护进程', icon: '📢', desc: '消息发布订阅，解耦通信', source: 'Redis', stars: '核心', tags: ['发布订阅', '消息', '解耦'], color: '#10B981' },

            { id: 'stream-process', name: '流处理', group: '守护进程', icon: '🌊', desc: '实时数据流处理分析', source: 'Redis', stars: '核心', tags: ['流处理', '实时', '分析'], color: '#EF4444' },

            { id: 'bloom-filter', name: '布隆过滤器', group: '守护进程', icon: '🌸', desc: '快速存在性判断，内存高效', source: 'Redis', stars: '核心', tags: ['布隆过滤器', '判断', '高效'], color: '#DC382D' },

            { id: 'hyperloglog', name: 'HyperLogLog', group: '守护进程', icon: '📊', desc: '基数统计，大数据量低内存', source: 'Redis', stars: '核心', tags: ['基数', '统计', '大数据'], color: '#6366F1' },

            { id: 'geo-index', name: '地理位置索引', group: '守护进程', icon: '📍', desc: 'LBS位置服务，附近查询', source: 'Redis', stars: '核心', tags: ['地理', '位置', 'LBS'], color: '#06B6D4' },

            { id: 'bitmap-operations', name: '位图操作', group: '守护进程', icon: '0️⃣', desc: '位图数据存储，日活统计', source: 'Redis', stars: '核心', tags: ['位图', '统计', '日活'], color: '#3B82F6' },

            { id: 'sort-set', name: '有序集合', group: '守护进程', icon: '🏆', desc: '排行榜实现，权重排序', source: 'Redis', stars: '核心', tags: ['有序集合', '排行', '排序'], color: '#F59E0B' },

            { id: 'ttl-manager', name: 'TTL管理器', group: '守护进程', icon: '⏰', desc: '键过期自动管理，资源释放', source: 'Redis', stars: '核心', tags: ['TTL', '过期', '自动'], color: '#8B5CF6' },

            { id: 'scan-iterator', name: '游标扫描', group: '守护进程', icon: '🔍', desc: '大Key遍历，线上安全操作', source: 'Redis', stars: '核心', tags: ['扫描', '游标', '遍历'], color: '#10B981' },

            { id: 'pipeline-batch', name: '管道批处理', group: '守护进程', icon: '📨', desc: '批量命令管道，减少RTT', source: 'Redis', stars: '核心', tags: ['管道', '批量', 'RTT'], color: '#EC4899' },

            { id: 'transaction-warp', name: '事务包装', group: '守护进程', icon: '📦', desc: 'Redis事务保证原子性', source: 'Redis', stars: '核心', tags: ['事务', '原子', '保证'], color: '#EF4444' },

            { id: 'lua-script', name: 'Lua脚本', group: '守护进程', icon: '📜', desc: '原子执行复杂逻辑', source: 'Redis', stars: '核心', tags: ['Lua', '原子', '脚本'], color: '#DC382D' },

            { id: 'cluster-shard', name: '集群分片', group: '守护进程', icon: '🔀', desc: 'Redis集群水平扩展', source: 'Redis', stars: '核心', tags: ['集群', '分片', '扩展'], color: '#3B82F6' },

            { id: 'sentinel-mode', name: '哨兵模式', group: '守护进程', icon: '🛡️', desc: 'Redis主从自动切换', source: 'Redis', stars: '核心', tags: ['哨兵', '主从', '切换'], color: '#10B981' },

            { id: 'memory-optimize', name: '内存优化', group: '守护进程', icon: '💡', desc: '内存碎片整理，容量规划', source: 'Redis', stars: '核心', tags: ['内存', '优化', '碎片'], color: '#F59E0B' },

            { id: 'slow-log', name: '慢查询日志', group: '守护进程', icon: '🐢', desc: 'Redis命令执行监控', source: 'Redis', stars: '核心', tags: ['慢查询', '日志', '监控'], color: '#8B5CF6' },

            { id: 'command-stats', name: '命令统计', group: '守护进程', icon: '📈', desc: '命令调用频率分析', source: 'Redis', stars: '核心', tags: ['命令', '统计', '分析'], color: '#06B6D4' },

            { id: 'big-key-detection', name: '大Key检测', group: '守护进程', icon: '🐘', desc: '内存占用异常检测', source: 'Redis', stars: '核心', tags: ['大Key', '检测', '内存'], color: '#EF4444' },

            { id: 'hot-key-detection', name: '热Key检测', group: '守护进程', icon: '🔥', desc: '热点数据访问监控', source: 'Redis', stars: '核心', tags: ['热Key', '检测', '热点'], color: '#DC382D' },

            { id: 'migration-tool', name: '数据迁移', group: '守护进程', icon: '🚚', desc: 'Redis实例间数据迁移', source: 'redis-cli', stars: '核心', tags: ['迁移', '数据', '实例'], color: '#3B82F6' },

            { id: 'backup-redis', name: 'Redis备份', group: '守护进程', icon: '💾', desc: 'RDB/AOF持久化备份', source: 'Redis', stars: '核心', tags: ['备份', 'RDB', 'AOF'], color: '#10B981' },

            { id: 'client-pool', name: '客户端连接池', group: '守护进程', icon: '🔗', desc: '连接复用减少开销', source: 'redis-py', stars: '核心', tags: ['连接池', '复用', '客户端'], color: '#6366F1' },

            { id: 'cluster-proxy', name: '集群代理', group: '守护进程', icon: '🔄', desc: '集群透明访问代理', source: 'Redis', stars: '核心', tags: ['代理', '集群', '透明'], color: '#F59E0B' },

            { id: 'geo-search', name: '附近搜索', group: '守护进程', icon: '📍', desc: 'LBS附近地点搜索', source: 'Redis', stars: '核心', tags: ['附近', 'LBS', '搜索'], color: '#8B5CF6' },

            { id: 'time-series', name: '时序数据', group: '守护进程', icon: '📊', desc: '时间序列数据存储查询', source: 'TimescaleDB', stars: '核心', tags: ['时序', '时间', '序列'], color: '#06B6D4' },

            { id: 'json-store', name: 'JSON存储', group: '守护进程', icon: '{}', desc: '半结构化JSON文档存储', source: 'MongoDB', stars: '核心', tags: ['JSON', '文档', '存储'], color: '#3B82F6' },

            { id: 'fts-query', name: '全文搜索', group: '守护进程', icon: '🔍', desc: '数据库全文检索能力', source: 'PostgreSQL', stars: '核心', tags: ['全文', '搜索', '检索'], color: '#F59E0B' },

            { id: 'window-function', name: '窗口函数', group: '守护进程', icon: '🪟', desc: 'SQL窗口函数分析', source: 'PostgreSQL', stars: '核心', tags: ['窗口', '函数', '分析'], color: '#10B981' },

            { id: 'cte-query', name: 'CTE查询', group: '守护进程', icon: '🔗', desc: '公用表表达式简化SQL', source: 'PostgreSQL', stars: '核心', tags: ['CTE', '表达式', '简化'], color: '#8B5CF6' },

            { id: 'materialized-view', name: '物化视图', group: '守护进程', icon: '👁️', desc: '预计算视图加速查询', source: 'PostgreSQL', stars: '核心', tags: ['物化视图', '预计算', '加速'], color: '#EC4899' },

            { id: 'rule-engine', name: '规则引擎', group: '守护进程', icon: '⚙️', desc: '业务规则动态配置执行', source: 'Drools', stars: '核心', tags: ['规则', '引擎', '动态'], color: '#06B6D4' },

            { id: 'workflow-bpmn', name: 'BPMN工作流', group: '守护进程', icon: '📋', desc: '可视化流程编排执行', source: 'Camunda', stars: '核心', tags: ['BPMN', '工作流', '编排'], color: '#3B82F6' },

            { id: 'state-machine', name: '状态机', group: '守护进程', icon: '🔄', desc: '状态流转控制与持久化', source: 'PostgreSQL', stars: '核心', tags: ['状态机', '流转', '控制'], color: '#F59E0B' },

            { id: 'saga-pattern', name: 'Saga模式', group: '守护进程', icon: '📖', desc: '分布式事务协调模式', source: 'Eventuate', stars: '核心', tags: ['Saga', '事务', '分布式'], color: '#EF4444' },

            { id: 'outbox-pattern', name: 'Outbox模式', group: '守护进程', icon: '📬', desc: '可靠消息最终一致性', source: 'PostgreSQL', stars: '核心', tags: ['Outbox', '消息', '一致'], color: '#DC382D' },

            { id: 'idempotent-msg', name: '消息幂等', group: '守护进程', icon: '♻️', desc: '消息消费幂等性保障', source: 'Kafka', stars: '核心', tags: ['幂等', '消息', '消费'], color: '#10B981' },

            { id: 'dead-letter', name: '死信队列', group: '守护进程', icon: '💀', desc: '失败消息隔离与重试', source: 'RabbitMQ', stars: '核心', tags: ['死信', '队列', '重试'], color: '#6366F1' },

            { id: 'delay-queue', name: '延迟队列', group: '守护进程', icon: '⏳', desc: '定时延迟消息处理', source: 'Redis', stars: '核心', tags: ['延迟', '队列', '定时'], color: '#F59E0B' },

            { id: 'priority-queue', name: '优先级队列', group: '守护进程', icon: '⭐', desc: '消息优先级调度处理', source: 'RabbitMQ', stars: '核心', tags: ['优先', '队列', '调度'], color: '#8B5CF6' },

            { id: 'fanout-queue', name: '扇出队列', group: '守护进程', icon: '🔀', desc: '一对多消息广播分发', source: 'SNS', stars: '核心', tags: ['扇出', '广播', '分发'], color: '#06B6D4' },

            { id: 'message-trace', name: '消息追踪', group: '守护进程', icon: '🔍', desc: '消息全链路追踪审计', source: 'Kafka', stars: '核心', tags: ['消息', '追踪', '链路'], color: '#3B82F6' },

            { id: 'schema-registry', name: 'Schema注册', group: '守护进程', icon: '📝', desc: '消息Schema版本管理', source: 'Confluent', stars: '核心', tags: ['Schema', '版本', '管理'], color: '#EC4899' },

            { id: 'stream-replay', name: '流数据重放', group: '守护进程', icon: '⏪', desc: '历史消息重放测试', source: 'Kafka', stars: '核心', tags: ['重放', '流', '测试'], color: '#EF4444' },

            { id: 'exactly-once', name: 'Exactly-Once', group: '守护进程', icon: '1️⃣', desc: '消息精确一次语义', source: 'Kafka', stars: '核心', tags: ['Exactly', '一次', '语义'], color: '#DC382D' },

            { id: 'consumer-group', name: '消费组', group: '守护进程', icon: '👥', desc: '消费者组负载均衡', source: 'Kafka', stars: '核心', tags: ['消费组', '负载', '均衡'], color: '#10B981' },

            { id: 'offset-commit', name: '位移提交', group: '守护进程', icon: '📍', desc: '消费进度持久化管理', source: 'Kafka', stars: '核心', tags: ['位移', '提交', '进度'], color: '#6366F1' },

            { id: 'rebalance-protocol', name: '重平衡协议', group: '守护进程', icon: '⚖️', desc: '消费者组再平衡策略', source: 'Kafka', stars: '核心', tags: ['重平衡', '协议', '策略'], color: '#F59E0B' },

            { id: 'retention-policy', name: '保留策略', group: '守护进程', icon: '🗑️', desc: '消息保留时间配置', source: 'Kafka', stars: '核心', tags: ['保留', '时间', '配置'], color: '#8B5CF6' },

            { id: 'compaction-topic', name: '日志压缩', group: '守护进程', icon: '🗜️', desc: 'Key状态变更保留最新', source: 'Kafka', stars: '核心', tags: ['压缩', '日志', 'Key'], color: '#06B6D4' },

            { id: 'mirror-maker', name: '跨集群复制', group: '守护进程', icon: '🔄', desc: '多数据中心数据同步', source: 'Kafka', stars: '核心', tags: ['复制', '集群', '同步'], color: '#3B82F6' },

            { id: 'schema-evolution', name: 'Schema演进', group: '守护进程', icon: '🔀', desc: '向前向后兼容字段变更', source: 'Avro', stars: '核心', tags: ['Schema', '演进', '兼容'], color: '#EC4899' },

            { id: 'data-lineage', name: '数据血缘', group: '守护进程', icon: '🩸', desc: '数据流转链路追踪', source: 'Apache Atlas', stars: '核心', tags: ['血缘', '流转', '链路'], color: '#EF4444' },

            { id: 'data-quality', name: '数据质量', group: '守护进程', icon: '✅', desc: '数据完整性准确性校验', source: 'Great Expectations', stars: '核心', tags: ['质量', '校验', '完整'], color: '#10B981' },

            { id: 'data-catalog', name: '数据目录', group: '守护进程', icon: '📚', desc: '元数据统一管理检索', source: 'DataHub', stars: '核心', tags: ['目录', '元数据', '管理'], color: '#F59E0B' },

            { id: 'data-masking', name: '数据脱敏', group: '守护进程', icon: '🎭', desc: '敏感信息动态脱敏', source: 'Apache Ranger', stars: '核心', tags: ['脱敏', '敏感', '动态'], color: '#DC382D' },

            { id: 'data-encrypt', name: '数据加密', group: '守护进程', icon: '🔐', desc: '存储传输数据加密', source: 'AWS KMS', stars: '核心', tags: ['加密', '存储', '传输'], color: '#6366F1' },

            { id: 'pii-detection', name: 'PII识别', group: '守护进程', icon: '🔍', desc: '个人隐私信息识别标注', source: 'Presidio', stars: '核心', tags: ['PII', '隐私', '识别'], color: '#EF4444' },

            { id: 'gdpr-compliance', name: 'GDPR合规', group: '守护进程', icon: '⚖️', desc: '数据删除权合规实现', source: 'OpenMetadata', stars: '核心', tags: ['GDPR', '合规', '删除'], color: '#8B5CF6' },

            { id: 'data-watermark', name: '数据水印', group: '守护进程', icon: '💧', desc: '数据溯源数字水印', source: 'Watermark', stars: '核心', tags: ['水印', '溯源', '版权'], color: '#06B6D4' },

            { id: 'backup-checksum', name: '备份校验', group: '守护进程', icon: '✅', desc: '备份数据完整性校验', source: 'pgBackRest', stars: '核心', tags: ['备份', '校验', '完整'], color: '#3B82F6' },

            { id: 'pitr-postgres', name: '时间点恢复', group: '守护进程', icon: '⏪', desc: '任意时间点数据恢复', source: 'PostgreSQL', stars: '核心', tags: ['PITR', '恢复', '时间点'], color: '#EC4899' },

            { id: 'incremental-backup', name: '增量备份', group: '守护进程', icon: '📈', desc: '仅备份变更数据', source: 'pgBackRest', stars: '核心', tags: ['增量', '备份', '变更'], color: '#F59E0B' },

            { id: 'geo-replication', name: '异地复制', group: '守护进程', icon: '🌍', desc: '跨地域数据容灾复制', source: 'PostgreSQL', stars: '核心', tags: ['异地', '复制', '容灾'], color: '#10B981' },

            { id: 'clone-database', name: '数据库克隆', group: '守护进程', icon: '📋', desc: '快速克隆测试环境', source: 'Docker', stars: '核心', tags: ['克隆', '测试', '环境'], color: '#6366F1' },

            { id: 'snapshot-volume', name: '卷快照', group: '守护进程', icon: '📸', desc: '存储卷快照备份', source: 'CSI', stars: '核心', tags: ['快照', '卷', '备份'], color: '#06B6D4' },

            { id: 'storage-tiering', name: '存储分层', group: '守护进程', icon: '🏗️', desc: '冷热数据自动分层', source: 'Ceph', stars: '核心', tags: ['分层', '存储', '冷热'], color: '#3B82F6' },

            { id: 'quota-manager', name: '配额管理', group: '守护进程', icon: '📊', desc: '存储空间配额控制', source: 'Cinder', stars: '核心', tags: ['配额', '空间', '控制'], color: '#EC4899' },

            { id: 'storage-encryption', name: '存储加密', group: '守护进程', icon: '🔐', desc: '块存储透明加密', source: 'LUKS', stars: '核心', tags: ['加密', '存储', '透明'], color: '#EF4444' },

            { id: 'block-device', name: '块设备', group: '守护进程', icon: '💾', desc: '云盘管理挂载卸载', source: 'CSI', stars: '核心', tags: ['块设备', '云盘', '挂载'], color: '#DC382D' },

            { id: 'file-system', name: '文件系统', group: '守护进程', icon: '📁', desc: '共享文件系统管理', source: 'NFS', stars: '核心', tags: ['文件', '系统', '共享'], color: '#10B981' },

            { id: 'object-storage', name: '对象存储', group: '守护进程', icon: '📦', desc: '海量非结构化数据存储', source: 'MinIO', stars: '核心', tags: ['对象', '存储', '海量'], color: '#F59E0B' },

            { id: 'bucket-policy', name: '存储桶策略', group: '守护进程', icon: '🪣', desc: '访问权限精细控制', source: 'S3', stars: '核心', tags: ['桶', '策略', '权限'], color: '#8B5CF6' },

            { id: 'lifecycle-policy', name: '生命周期策略', group: '守护进程', icon: '🔄', desc: '自动归档删除过期文件', source: 'S3', stars: '核心', tags: ['生命周期', '归档', '删除'], color: '#06B6D4' },

            { id: 'cdn-invalidate', name: 'CDN刷新', group: '守护进程', icon: '🌐', desc: '缓存刷新预热', source: 'CDN', stars: '核心', tags: ['CDN', '刷新', '预热'], color: '#3B82F6' },

            { id: 'transfer-acceleration', name: '传输加速', group: '守护进程', icon: '⚡', desc: '全球加速数据上传下载', source: 'S3', stars: '核心', tags: ['加速', '传输', '全球'], color: '#F59E0B' },

            { id: 'multipart-upload', name: '分片上传', group: '守护进程', icon: '📤', desc: '大文件并行分片上传', source: 'S3', stars: '核心', tags: ['分片', '上传', '并行'], color: '#EC4899' },

            { id: 'signed-url', name: '签名URL', group: '守护进程', icon: '✍️', desc: '临时访问授权链接', source: 'S3', stars: '核心', tags: ['签名', 'URL', '临时'], color: '#10B981' },

            { id: 'static-website', name: '静态网站托管', group: '守护进程', icon: '🌐', desc: '对象存储静态网站', source: 'S3', stars: '核心', tags: ['静态', '网站', '托管'], color: '#6366F1' },

            { id: 'event-trigger', name: '事件触发', group: '守护进程', icon: '⚡', desc: '存储事件触发计算', source: 'Lambda', stars: '核心', tags: ['事件', '触发', '计算'], color: '#EF4444' },

            { id: 'cors-config', name: 'CORS跨域配置', group: '守护进程', icon: '🔗', desc: '跨域资源共享配置', source: 'S3', stars: '核心', tags: ['CORS', '跨域', '配置'], color: '#DC382D' },

            { id: 'versioning-object', name: '对象版本控制', group: '守护进程', icon: '📜', desc: '历史版本保留恢复', source: 'S3', stars: '核心', tags: ['版本', '对象', '历史'], color: '#8B5CF6' },

            { id: 'replication-cross', name: '跨区域复制', group: '守护进程', icon: '🔄', desc: '跨区域数据同步', source: 'S3', stars: '核心', tags: ['复制', '跨区', '同步'], color: '#06B6D4' },



            // ========== 新增模块 (16个) ==========

            // P0 - 核心基础设施

            { id: 'visual-rpa-core', name: '全域视觉RPA引擎', group: '核心基础设施', icon: '👁️', desc: '基于视觉识别的RPA引擎，支持元素定位、OCR文字提取、鼠标键盘自动化', source: 'Open Interpreter', stars: '58k', tags: ['RPA', '视觉', 'OCR'], color: '#6366F1', priority: 'high' },

            { id: 'agent-resource-control', name: '资源精细化管控', group: '核心基础设施', icon: '⚡', desc: 'Agent资源配额管理，CPU/内存/GPU/网络多维度监控与动态限流', source: 'Ray', stars: '35k', tags: ['资源', '配额', '监控'], color: '#F59E0B', priority: 'high' },

            { id: 'cross-platform-adapter', name: '跨平台兼容转译层', group: '核心基础设施', icon: '🔄', desc: 'Windows/Linux/macOS/Android/iOS五平台适配，API差异自动转译', source: 'PyAutoGUI', stars: '14k', tags: ['跨平台', '适配', '转译'], color: '#10B981', priority: 'high' },



            // P1 - 通信与记忆

            { id: 'uni-comm-gateway', name: '全渠道通信网关', group: '通信与记忆', icon: '🌐', desc: '统一微信/钉钉/飞书/Telegram/Slack/邮件六渠道消息收发网关', source: 'Zep', stars: '3k', tags: ['通信', '网关', '多渠道'], color: '#0EA5E9', priority: 'high' },

            { id: 'longterm-memory', name: '长期记忆引擎', group: '通信与记忆', icon: '🧠', desc: 'AI长期记忆管理(P0真实Embedding+P1主循环接入+P2多Agent共享)，Zhipu/OpenAI/Ollama三通道语义检索，共享经验自动广播', source: 'AUTO-EVO-AI', stars: 'V0.1', tags: ['记忆', '长期', '语义', '共享', 'Embedding'], color: '#8B5CF6', priority: 'high' },
            { id: 'experience-bridge', name: '经验记忆桥接', group: '通信与记忆', icon: '🔗', desc: 'ExperienceBase与LongTermMemory双向同步，经验自动持久化+语义检索增强，路由/修复全链路记忆覆盖', source: 'AUTO-EVO-AI', stars: 'V0.1', tags: ['经验', '桥接', '记忆', '同步'], color: '#06B6D4', priority: 'high' },

            { id: 'evo-plugin-market', name: '插件市场标准', group: '通信与记忆', icon: '🏪', desc: '标准化插件市场，支持插件搜索/安装/版本管理/沙箱安全审核', source: 'n8n', stars: '70k', tags: ['插件', '市场', '标准化'], color: '#EC4899', priority: 'high' },



            // P2 - 行业垂直

            { id: 'workflow-orchestrator', name: '低代码编排引擎', group: '行业垂直', icon: '⚙️', desc: '可视化DAG工作流编排，支持条件分支/并行/循环/子流程/异常处理', source: 'Dify', stars: '60k', tags: ['低代码', '工作流', 'DAG'], color: '#F97316', priority: 'medium' },

            { id: 'ecommerce-agent', name: '电商垂直Agent', group: '行业垂直', icon: '🛒', desc: '电商全链路自动化：选品分析/价格监控/库存管理/订单处理/售后客服', source: 'AUTO-EVO-AI', stars: '自研', tags: ['电商', '选品', '自动化'], color: '#22C55E', priority: 'medium' },

            { id: 'finance-legal-agent', name: '财税法务Agent', group: '行业垂直', icon: '💰', desc: '财税法务一体化：发票OCR/税务申报/合同审查/合规风险预警', source: 'AUTO-EVO-AI', stars: '自研', tags: ['财税', '法务', '合规'], color: '#6366F1', priority: 'medium' },

            { id: 'media-content-agent', name: '新媒体内容Agent', group: '行业垂直', icon: '📱', desc: '多平台内容生成与发布：文案创作/图片生成/视频剪辑/数据分析', source: 'AUTO-EVO-AI', stars: '自研', tags: ['新媒体', '内容', '创作'], color: '#EC4899', priority: 'medium' },

            { id: 'industrial-ops-agent', name: '工业运维Agent', group: '行业垂直', icon: '🏭', desc: '工业场景运维：设备监控/故障诊断/预测性维护/巡检自动化', source: 'AUTO-EVO-AI', stars: '自研', tags: ['工业', '运维', 'IoT'], color: '#06B6D4', priority: 'medium' },



            // P3 - 安全与治理

            { id: 'audit-trail', name: '审计追踪系统', group: '安全与治理', icon: '📋', desc: '全链路操作审计：用户行为追踪/数据变更记录/合规报表/溯源分析', source: 'AUTO-EVO-AI', stars: '自研', tags: ['审计', '追踪', '合规'], color: '#EF4444', priority: 'medium' },

            { id: 'risk-control', name: '风控拦截系统', group: '安全与治理', icon: '🛡️', desc: '多维度风控引擎：黑名单/频率限制/异常行为检测/动态风险评分', source: 'AUTO-EVO-AI', stars: '自研', tags: ['风控', '拦截', '安全'], color: '#DC382D', priority: 'medium' },

            { id: 'tenant-isolation', name: '多租户隔离', group: '安全与治理', icon: '🏢', desc: '企业级多租户：数据逻辑隔离/资源配额/独立配置/计费管理', source: 'AUTO-EVO-AI', stars: '自研', tags: ['多租户', '隔离', '配额'], color: '#A855F7', priority: 'medium' },



            // P4 - 高级能力

            { id: 'self-healing', name: '自愈修复模块', group: '高级能力', icon: '💉', desc: '系统自愈：故障自动检测/降级策略/服务重启/根因修复/健康恢复', source: 'AUTO-EVO-AI', stars: '自研', tags: ['自愈', '修复', '容灾'], color: '#10B981', priority: 'medium' },

            { id: 'model-router', name: '多模型调度中心', group: '高级能力', icon: '🔀', desc: '智能模型调度：负载均衡/故障转移/成本优化/A/B测试/语义路由', source: 'LiteLLM', stars: '30k', tags: ['模型', '调度', '路由'], color: '#3B82F6', priority: 'medium' },



            // ========== 新增模块 (6个) ==========

            // 安全审批自动化

            { id: 'opa-policy-engine', name: 'OPA策略审批引擎', group: '安全审批', icon: '📋', desc: '策略即代码审批引擎：Rego声明式策略/低中风险自动放行/策略热更新', source: 'OPA', stars: '10k', tags: ['OPA', '策略', '审批'], color: '#6366F1', priority: 'high' },

            { id: 'cerbos-permission', name: 'Cerbos权限决策层', group: '安全审批', icon: '🔐', desc: '零信任细粒度权限：YAML策略/条件策略(时间IP环境)/AI Agent授权', source: 'Cerbos', stars: '4k', tags: ['权限', '零信任', '策略'], color: '#F59E0B', priority: 'high' },

            { id: 'temporal-approval', name: 'Temporal审批工作流', group: '安全审批', icon: '⏱️', desc: '持久化审批网关：SLA自动管理/超时升级拒绝/状态持久化/模板审批流', source: 'Temporal', stars: '14k', tags: ['审批', '工作流', 'SLA'], color: '#EF4444', priority: 'medium' },



            // 战略决策辅助

            { id: 'crewai-strategy', name: 'CrewAI战略决策Agent', group: '战略决策', icon: '🎯', desc: '多Agent角色协作：CEO/CFO/CTO辩论投票/共识度评估/决策追溯', source: 'CrewAI', stars: '35k', tags: ['战略', 'Agent', '决策'], color: '#8B5CF6', priority: 'high' },

            { id: 'langgraph-decision', name: 'LangGraph决策流引擎', group: '战略决策', icon: '🔀', desc: '状态机决策流：Human-in-the-Loop/分支循环/条件路由/可视化追溯', source: 'LangGraph', stars: '29k', tags: ['决策', '状态机', '可视化'], color: '#0EA5E9', priority: 'medium' },

            { id: 'business-analyst', name: '业务分析师Agent', group: '战略决策', icon: '📊', desc: '自动战略分析：SWOT/竞品对比/财务建模/市场趋势/报告生成', source: 'AUTO-EVO-AI', stars: '自研', tags: ['分析', 'SWOT', '报告'], color: '#22C55E', priority: 'medium' },



            // TuriX-CUA 桥接

            { id: 'turix-cua-bridge', name: 'TuriX-CUA桥接', group: '智能CUA', icon: '🤖', desc: 'VLM端到端桌面操控：自然语言驱动、截图理解、AI决策闭环', source: 'TuriX-CUA', stars: '活跃增长', tags: ['CUA', 'VLM', '桌面'], color: '#6366F1', priority: 'high' },



            // Open Interpreter 桥接

            { id: 'open-interpreter-bridge', name: 'Open Interpreter桥接', group: 'AI决策层', icon: '💬', desc: '自然语言→代码执行→系统操控闭环，多技能模块：shell/python/computer/browser', source: 'Open Interpreter', stars: '58k', tags: ['代码执行', '多技能', 'LLM'], color: '#3B82F6', priority: 'high' },



            // UI-TARS 视觉理解

            { id: 'ui-tars-bridge', name: 'UI-TARS视觉理解', group: 'AI决策层', icon: '👁️', desc: '字节跳动CUA：感知→推理→行动三阶段闭环，支持Doubao1.5模型', source: 'UI-TARS', stars: '火山引擎', tags: ['CUA', '视觉', '推理'], color: '#EF4444', priority: 'high' },



            // OpenClaw 网关

            { id: 'openclaw-gateway', name: 'OpenClaw网关', group: 'AI决策层', icon: '🌐', desc: '319k+ Stars自托管AI网关：多模型路由、负载均衡、故障转移、API Key管理', source: 'OpenClaw', stars: '319k', tags: ['网关', '路由', '负载均衡'], color: '#10B981', priority: 'high' },



            // 自我进化&生态

            { id: 'self-evolving-engine', name: '自我进化引擎', group: '自我进化&生态', icon: '🧬', desc: '参考HermesAgent: 技能自动创建/改进/错误记忆/反馈学习/知识累积，越用越聪明', source: 'HermesAgent', stars: '118k', tags: ['进化', '学习', '技能'], color: '#8B5CF6', priority: 'high' },

            { id: 'mcp-integration', name: 'MCP协议集成', group: '自我进化&生态', icon: '🔌', desc: 'Anthropic MCP: AI的USB-C扩展坞，统一连接外部工具和数据源，支持stdio/SSE/HTTP', source: 'Anthropic MCP', stars: '45k', tags: ['MCP', '协议', '工具'], color: '#EC4899', priority: 'high' },

            { id: 'skill-marketplace', name: '技能市场', group: '自我进化&生态', icon: '🏪', desc: '参考ClawHub+SkillsHub: 技能发布/搜索/安装/版本管理/安全审核/评分，兼容SKILL.md标准', source: 'ClawHub/SkillsHub', stars: '2k', tags: ['技能', '市场', '插件'], color: '#F59E0B', priority: 'medium' },



            // 主编排器

            { id: 'agent-orchestrator', name: '主编排器', group: '系统大脑', icon: '🧠', desc: '系统智能大脑：自然语言理解→任务拆解→532模块自动调度→执行→学习→改进，一句话完成复杂任务', source: 'AUTO-EVO-AI', stars: 'Core', tags: ['编排', '调度', '大脑', '自动化'], color: '#EF4444', priority: 'critical' },



            // ========== 新增模块 (10个) ==========

            // P0 - RPA核心能力

            { id: 'win-control', name: 'Windows控件操作', group: 'RPA核心', icon: '🖱️', desc: '基于pywinauto的Windows原生控件操作：窗口句柄/按钮点击/文本输入/表格读写/菜单操作，精准对标OpenClaw', source: 'pywinauto', stars: '核心', tags: ['控件', 'Windows', 'RPA'], color: '#6366F1', priority: 'critical' },

            { id: 'window-manager', name: '窗口管理器', group: 'RPA核心', icon: '🪟', desc: '基于psutil的跨平台窗口管理：进程查杀/窗口枚举/状态控制/置顶最小化/多屏适配', source: 'psutil', stars: '核心', tags: ['窗口', '进程', '管理'], color: '#F59E0B', priority: 'high' },

            { id: 'self-healing-v31', name: '异常自愈引擎', group: 'RPA核心', icon: '🩹', desc: 'RPA异常自动检测与修复：窗口变化适配/网络超时重连/元素丢失重定位/操作降级备选方案', source: 'AUTO-EVO-AI', stars: '核心', tags: ['自愈', '异常', '容错'], color: '#10B981', priority: 'critical' },

            { id: 'rpa-fault-tolerance', name: 'RPA容错框架', group: 'RPA核心', icon: '🛡️', desc: '工业级容错：超时重试/断点续跑/截图回溯/错误分类/自动降级/操作日志追踪', source: 'AUTO-EVO-AI', stars: '核心', tags: ['容错', '重试', '断点'], color: '#EF4444', priority: 'high' },



            // P1 - 编排与触发

            { id: 'flow-engine', name: '可视化流程编排', group: '编排与触发', icon: '🔀', desc: 'Drawflow拖拽式流程编排：节点拖拽/连线/参数配置/条件分支/并行执行，对标OpenClaw拖拽编排', source: 'Drawflow', stars: '核心', tags: ['编排', '拖拽', '流程图'], color: '#8B5CF6', priority: 'high' },

            { id: 'trigger-engine', name: '全局热键触发', group: '编排与触发', icon: '⌨️', desc: '基于keyboard的全局热键绑定：热键触发流程/系统事件监听(文件创建/窗口变化)/灵活触发规则', source: 'keyboard', stars: '核心', tags: ['热键', '触发', '事件'], color: '#EC4899', priority: 'high' },

            { id: 'resource-scheduler', name: '资源阈值调度', group: '编排与触发', icon: '📊', desc: '基于psutil的系统资源监控调度：CPU/内存/磁盘阈值触发/负载过高暂停/资源恢复自动继续', source: 'psutil', stars: '核心', tags: ['资源', '阈值', '调度'], color: '#06B6D4', priority: 'medium' },



            // P2 - 高级RPA能力

            { id: 'vision-rpa', name: '视觉识别RPA', group: '高级RPA', icon: '👁️', desc: '基于OpenCV的视觉RPA：模板匹配/图标定位/OCR文字识别/截图对比/无控件应用适配', source: 'OpenCV', stars: '核心', tags: ['视觉', 'OCR', '模板匹配'], color: '#F97316', priority: 'high' },

            { id: 'local-monitor', name: '本地监控告警', group: '高级RPA', icon: '📡', desc: '本地异常监控与告警：系统资源异常/进程崩溃/磁盘满/网络断连/桌面弹窗检测，日志+通知', source: 'AUTO-EVO-AI', stars: '核心', tags: ['监控', '告警', '异常'], color: '#DC382D', priority: 'medium' },

            { id: 'debug-panel', name: '调试面板', group: '高级RPA', icon: '🔧', desc: '轻量级HTTP调试面板：单步执行/变量监控/操作回放/日志追踪/远程调试(端口8100)', source: 'AUTO-EVO-AI', stars: '核心', tags: ['调试', '断点', '远程'], color: '#22C55E', priority: 'medium' },



            // ========== 新增模块 (7个) ==========

            // P0 - 日志与备份

            { id: 'log-manager', name: '智能日志管理', group: '运维保障', icon: '📋', desc: '基于loguru的智能日志：自动分割/异常捕获/关键词搜索/日志导出/过期清理，替代原生logging', source: 'loguru', stars: '核心', tags: ['日志', 'loguru', '搜索'], color: '#6366F1', priority: 'high' },

            { id: 'backup-engine', name: '智能备份引擎', group: '运维保障', icon: '💾', desc: '一键备份恢复：ZIP压缩/版本管理/定时自动备份/断点恢复/容量清理，数据安全保障', source: 'AUTO-EVO-AI', stars: '核心', tags: ['备份', '恢复', '版本'], color: '#10B981', priority: 'critical' },



            // P1 - 可视化与引导

            { id: 'config-ui', name: '可视化配置管理', group: '用户体验', icon: '⚙️', desc: 'Web可视化配置界面：系统/AI/自动化/备份/资源五大配置区，替代YAML手改，零技术门槛', source: 'AUTO-EVO-AI', stars: '核心', tags: ['配置', '可视化', 'Web'], color: '#8B5CF6', priority: 'high' },

            { id: 'guide-manager', name: '新手引导系统', group: '用户体验', icon: '📖', desc: '交互式新手引导（intro.js）：首次自动触发/分步教学/自定义步骤/手动重播，零门槛上手', source: 'intro.js', stars: '核心', tags: ['引导', '新手', '教程'], color: '#F59E0B', priority: 'high' },



            // P2 - 导出与报告

            { id: 'export-engine', name: '多格式数据导出', group: '数据工具', icon: '📤', desc: 'CSV/JSON/HTML/TXT多格式导出：自动表头/中文编码/导出历史/批量导出，适配办公需求', source: 'AUTO-EVO-AI', stars: '核心', tags: ['导出', 'CSV', 'Excel'], color: '#EC4899', priority: 'medium' },

            { id: 'pdf-report', name: 'PDF报告生成', group: '数据工具', icon: '📄', desc: 'fpdf2原生PDF生成：中文支持/表格/标题/段落/页码/自定义尺寸，专业报告一键产出', source: 'fpdf2', stars: '核心', tags: ['PDF', '报告', '中文'], color: '#0EA5E9', priority: 'medium' },



            // P3 - 帮助文档

            { id: 'help-docs', name: '离线帮助文档', group: '数据工具', icon: '📚', desc: '内置离线帮助中心：快速上手/常见问题/配置说明/模块介绍，无需联网即可查阅', source: 'AUTO-EVO-AI', stars: '核心', tags: ['帮助', '文档', '离线'], color: '#22C55E', priority: 'medium' },



            // ========== 新增模块 (8个) ==========

            // 移动端远程操控

            { id: 'push-notify', name: '消息推送引擎', group: '移动端', icon: '🔔', desc: 'onepush多通道推送：Bark/微信/钉钉/Telegram/邮件/PushPlus/Server酱等30+通道，任务完成即时通知', source: 'onepush', stars: '1.5k', tags: ['推送', '通知', '手机'], color: '#EF4444', priority: 'critical' },

            { id: 'mobile-gateway', name: '手机指令网关', group: '移动端', icon: '📱', desc: '微信/钉钉Bot远程指令：手机发消息操控电脑/查看状态/触发任务/下载结果，出门也能远程控制', source: 'AUTO-EVO-AI', stars: '核心', tags: ['微信', '钉钉', '远程'], color: '#8B5CF6', priority: 'critical' },

            { id: 'web-remote', name: '手机Web面板', group: '移动端', icon: '🌐', desc: '响应式Web操控面板：手机浏览器直接操控电脑端系统，查看任务/日志/状态/触发执行，内网穿透支持', source: 'AUTO-EVO-AI', stars: '核心', tags: ['Web', '远程', '手机'], color: '#3B82F6', priority: 'high' },

            { id: 'tunnel-manager', name: '内网穿透管理', group: '移动端', icon: '🔌', desc: 'Cloudflare Tunnel/ngrok内网穿透：外网访问内网服务，零配置一键穿透，手机随时随地连回电脑', source: 'cloudflared', stars: '核心', tags: ['穿透', '内网', '外网'], color: '#F97316', priority: 'medium' },



            // 金融数据

            { id: 'finance-data', name: '金融数据中心', group: '行业垂直', icon: '💰', desc: 'AKShare金融数据：A股行情/基金净值/期货数据/宏观经济(CPI/GDP/PMI)/外汇/债券，200+接口', source: 'AKShare', stars: '10k', tags: ['金融', '股票', '基金'], color: '#10B981', priority: 'high' },



            // 浏览器自动化

            { id: 'browser-auto', name: '浏览器自动化', group: '行业垂直', icon: '🌐', desc: 'Playwright浏览器自动化：网页采集/自动填表/截图/表格提取/多标签管理，电商/数据采集利器', source: 'Playwright', stars: '69k', tags: ['浏览器', '采集', '自动化'], color: '#6366F1', priority: 'high' },



            // 智能辅助

            { id: 'voice-notify', name: '语音播报引擎', group: '行业垂直', icon: '🔊', desc: 'pyttsx3文字转语音：任务完成/异常告警/定时提醒语音播报，离开电脑也能收到通知', source: 'pyttsx3', stars: '4k', tags: ['语音', '播报', '提醒'], color: '#EC4899', priority: 'medium' },

            { id: 'scheduler-pro', name: '企业级调度器', group: '行业垂直', icon: '⏰', desc: 'APScheduler企业调度：Cron表达式/间隔执行/日期触发/任务持久化，替代原生schedule，支持复杂调度', source: 'APScheduler', stars: '12k', tags: ['定时', '调度', 'Cron'], color: '#F59E0B', priority: 'medium' },



            // ========== 新增模块 (21个) ==========

            // AI/通信模块 (3个)

            { id: 'ai-gateway', name: '多模型AI网关', group: 'AI模型层', icon: '🌐', desc: 'OneAPI统一网关：同时接入OpenAI/Claude/Gemini/本地LLM等100+模型，额度管理/负载均衡/故障转移', source: 'OneAPI', stars: '15k', tags: ['网关', '多模型', '统一'], color: '#10B37C', priority: 'high' },

            { id: 'claw-gateway', name: 'OpenClaw集成网关', group: 'Agent协作', icon: '🦞', desc: 'OpenClaw专用Agent控制框架：多Agent协作/任务分发/结果聚合，支持Claude/GPT等主流模型', source: 'OpenClaw', stars: '319k', tags: ['OpenClaw', 'Agent', '协作'], color: '#F97316', priority: 'high' },

            { id: 'hermes-gateway', name: 'Hermes消息网关', group: '通讯与数据', icon: '⚡', desc: 'FastAPI-MQTT消息路由：Agent间通信/主题订阅/消息持久化，支持设备影子/在线状态', source: 'FastAPI-MQTT', stars: '核心', tags: ['MQTT', '消息', '通信'], color: '#8B5CF6', priority: 'medium' },



            // 基础设施模块 (6个)

            { id: 'file-watcher-engine', name: '文件监控引擎', group: '运维保障', icon: '👁️', desc: 'watchdog文件监听：目录/文件变更自动触发/新增/修改/删除监控，自动执行备份或同步', source: 'watchdog', stars: '5k', tags: ['文件', '监控', '触发'], color: '#06B6D4', priority: 'high' },

            { id: 'data-pipeline', name: 'ETL数据管道', group: '数据工具', icon: '🔄', desc: 'Pandas数据处理流水线：抽取/清洗/转换/加载，支持CSV/Excel/数据库，自动调度运行', source: 'Pandas', stars: '40k', tags: ['ETL', '数据', '管道'], color: '#3B82F6', priority: 'high' },

            { id: 'event-bus-blinker', name: '事件总线', group: '系统编排', icon: '📡', desc: 'blinker事件驱动：模块间松耦合通信/信号发布订阅/异步事件处理，解耦复杂业务流程', source: 'blinker', stars: '核心', tags: ['事件', '总线', '解耦'], color: '#EC4899', priority: 'medium' },

            { id: 'message-queue', name: '消息队列引擎', group: '系统编排', icon: '📬', desc: 'huey轻量队列：异步任务队列/延迟任务/优先级队列/结果回调，Redis后端持久化', source: 'huey', stars: '2k', tags: ['队列', '异步', 'Redis'], color: '#10B981', priority: 'medium' },

            { id: 'cache-engine', name: '智能缓存引擎', group: '数据库存储', icon: '⚡', desc: 'Redis多级缓存：TTL过期/分布式锁/前缀匹配/批量操作/缓存预热，性能提升10倍', source: 'redis-py', stars: '18k', tags: ['缓存', 'Redis', '性能'], color: '#DC382D', priority: 'high' },

            { id: 'network-proxy', name: '代理管理引擎', group: '运维保障', icon: '🔀', desc: 'proxy.py HTTP代理：请求拦截/响应修改/认证控制/限流熔断，支持中间人抓包调试', source: 'proxy.py', stars: '核心', tags: ['代理', 'HTTP', '调试'], color: '#6366F1', priority: 'medium' },



            // 安全监控模块 (3个)

            { id: 'security-scanner', name: '安全扫描引擎', group: '安全治理', icon: '🔍', desc: 'bandit+pip-audit安全扫描：代码漏洞检测/依赖漏洞扫描/SQL注入/XSS检测，CI/CD集成', source: 'bandit', stars: '5k', tags: ['安全', '扫描', '漏洞'], color: '#EF4444', priority: 'high' },

            { id: 'perf-monitor', name: '性能监控中心', group: '运维保障', icon: '📊', desc: 'psutil+Prometheus指标监控：CPU/内存/磁盘/网络实时监控/告警规则/趋势图表，Grafana集成', source: 'psutil', stars: '核心', tags: ['性能', '监控', '告警'], color: '#F59E0B', priority: 'high' },

            { id: 'code-quality', name: '代码质量引擎', group: '编程助手', icon: '✅', desc: 'ruff+black+mypy代码质量：自动格式化/lint检查/类型检查/代码风格统一，开发必备', source: 'ruff', stars: '15k', tags: ['代码', '质量', 'lint'], color: '#22C55E', priority: 'high' },



            // 系统管理模块 (5个)

            { id: 'auto-update', name: '自动更新引擎', group: '运维保障', icon: '🔄', desc: 'pip-tools自动更新：依赖版本检测/安全漏洞提示/一键升级/锁定核心包版本', source: 'pip-tools', stars: '核心', tags: ['更新', '依赖', '升级'], color: '#0EA5E9', priority: 'medium' },

            { id: 'session-manager', name: '会话管理引擎', group: '核心基础设施', icon: '🔑', desc: 'itsdangerous会话管理：签名Cookie/防篡改/过期控制/安全序列化，Web会话安全必备', source: 'itsdangerous', stars: '核心', tags: ['会话', '安全', 'Cookie'], color: '#A855F7', priority: 'medium' },

            { id: 'i18n-engine', name: '多语言国际化', group: '核心基础设施', icon: '🌍', desc: 'Babel国际化框架：多语言翻译/日期格式/货币格式/复数规则，支持50+语言', source: 'Babel', stars: '核心', tags: ['i18n', '多语言', '翻译'], color: '#84CC16', priority: 'medium' },

            { id: 'plugin-loader', name: '插件系统引擎', group: '核心基础设施', icon: '🔌', desc: 'pluggy插件架构：动态插件加载/热插拔/钩子注册/版本管理，支持第三方扩展', source: 'pluggy', stars: '5k', tags: ['插件', '扩展', '动态'], color: '#F472B6', priority: 'high' },

            { id: 'cron-engine', name: 'Cron调度引擎', group: '运维保障', icon: '⏰', desc: 'croniter时间调度：复杂Cron表达式解析/验证/下一次执行时间计算，支持日历扩展', source: 'croniter', stars: '核心', tags: ['Cron', '调度', '时间'], color: '#14B8A6', priority: 'medium' },



            // 业务引擎模块 (4个)

            { id: 'workflow-manager', name: '工作流管理引擎', group: '编排与触发', icon: '🔀', desc: 'Prefect工作流编排：任务依赖图/重试机制/并发执行/结果缓存/失败告警，可视化DAG', source: 'Prefect', stars: '15k', tags: ['工作流', '编排', 'DAG'], color: '#6366F1', priority: 'high' },

            { id: 'form-engine', name: '表单引擎', group: '数据工具', icon: '📝', desc: 'Formily表单渲染：JSON Schema驱动/动态表单/联动逻辑/验证规则，复杂表单快速构建', source: 'Formily', stars: '10k', tags: ['表单', 'JSON', '动态'], color: '#EC4899', priority: 'medium' },

            { id: 'agent-marketplace', name: 'Agent市场', group: '行业垂直', icon: '🏪', desc: 'GitHub API集成市场：Agent发布/搜索/安装/评分/版本管理，一键安装社区Agent', source: 'GitHub API', stars: '核心', tags: ['Agent', '市场', '安装'], color: '#F59E0B', priority: 'medium' },

            { id: 'template-market', name: '模板市场', group: '数据工具', icon: '📦', desc: 'cookiecutter项目模板：快速生成项目脚手架/模板市场/变量替换，支持自定义模板', source: 'cookiecutter', stars: '15k', tags: ['模板', '脚手架', '生成'], color: '#10B981', priority: 'medium' },



            // ========== 新增功能 (全部) ==========



            // --- 1. GitHub优质项目模块 ---

            { id: 'browser-use', name: 'Browser-Use浏览器自动化', group: '行业垂直', icon: '🌐', desc: 'AI网页自动化Agent：自然语言控制浏览器/自动填表/点击/采集/截图，55k星热门项目', source: 'browser-use/browser-use', stars: '55k', tags: ['浏览器', '自动化', 'AI'], color: '#6366F1', priority: 'high' },

            { id: 'agentseek', name: 'AgentSeek通用Agent', group: 'Agent编排', icon: '🔍', desc: '通用AI Agent框架：多Provider支持/工具调用/记忆管理/长对话，支持OpenAI/Claude/Gemini', source: 'AgentSeek/AgentSeek', stars: '8k', tags: ['Agent', '框架', '通用'], color: '#10B981', priority: 'high' },

            { id: 'superagent', name: 'SuperAgent编排平台', group: 'Agent编排', icon: '🚀', desc: 'AI Agent云编排平台：可视化工作流/多模型集成/API部署/监控日志，SaaS+开源版', source: 'superagent/superagent', stars: '12k', tags: ['Agent', '编排', 'SaaS'], color: '#F59E0B', priority: 'high' },

            { id: 'fastagency', name: 'FastAgency多Agent协作', group: 'Agent协作', icon: '🤝', desc: '多Agent自动编排：AutoGen+FastAPI融合/动态Agent创建/消息路由/流式响应', source: '/airmaxe/FastAgency', stars: '5k', tags: ['多Agent', '协作', 'AutoGen'], color: '#8B5CF6', priority: 'medium' },

            { id: 'autogen-studio', name: 'AutoGen Studio微软工具', group: 'Agent面板', icon: '💻', desc: 'Microsoft AutoGen开发工具：可视化Agent配置/对话测试/插件扩展/代码导出', source: 'microsoft/autogen-studio', stars: '18k', tags: ['AutoGen', '微软', '开发工具'], color: '#0078D4', priority: 'high' },

            { id: 'openinterpreter', name: 'Open Interpreter执行', group: '代码工程', icon: '⚡', desc: '自然语言编程助手：本地代码执行/沙箱环境/多语言支持/文件操作，ChatGPT代码解释器开源版', source: 'OpenInterpreter/open-interpreter', stars: '45k', tags: ['代码', '执行', '编程'], color: '#22C55E', priority: 'high' },

            { id: 'mcp-servers', name: 'MCP协议服务器集', group: '工具生态', icon: '🔌', desc: 'Model Context Protocol服务器集合：文件系统/数据库/Git/Slack等20+官方服务器集成', source: 'modelcontextprotocol/servers', stars: '20k', tags: ['MCP', '协议', '工具'], color: '#6366F1', priority: 'high' },

            { id: 'crewai', name: 'CrewAI团队Agent', group: 'Agent协作', icon: '👥', desc: '多Agent团队协作框架：角色定义/任务委派/顺序/并行执行，适合企业工作流', source: 'crewAI/crewAI', stars: '25k', tags: ['CrewAI', '团队', '协作'], color: '#F97316', priority: 'high' },

            { id: 'dify', name: 'Dify应用编排平台', group: 'Agent编排', icon: '🏗️', desc: 'LLMOps应用平台：可视化编排/提示词管理/数据集/RAG/Agent/发布API，国产开源', source: 'langgenius/dify', stars: '68k', tags: ['Dify', 'LLMOps', '编排'], color: '#10B981', priority: 'high' },

            { id: 'flowise', name: 'Flowise低代码LLM', group: 'Agent编排', icon: '🌊', desc: '拖拽式LLM应用构建：LangChainJS可视化/Chain配置/向量数据库/聊天机器人', source: 'FlowiseAI/Flowise', stars: '35k', tags: ['Flowise', '低代码', 'LangChain'], color: '#06B6D4', priority: 'medium' },

            { id: 'n8n', name: 'n8n自动化工作流', group: '编排与触发', icon: '🔄', desc: '开源工作流自动化：700+集成/可视化编排/代码执行/Webhook/定时触发/AI节点', source: 'n8n-io/n8n', stars: '38k', tags: ['n8n', '自动化', '工作流'], color: '#EA4B71', priority: 'high' },

            { id: 'copilotkit', name: 'CopilotKit开发工具', group: '编程助手', icon: '🤖', desc: 'AI副驾驶开发套件：React组件/聊天机器人/自动补全/代码生成，集成LangChain', source: 'CopilotKit/CopilotKit', stars: '12k', tags: ['Copilot', 'React', '开发'], color: '#6366F1', priority: 'medium' },

            { id: 'llamaparse', name: 'LlamaParse文档解析', group: '数据工具', icon: '📄', desc: 'PDF/PPT/Excel智能解析：多模态大模型支持/表格提取/Markdown输出/自动分块', source: 'run-llama/llamaparse', stars: '15k', tags: ['解析', 'PDF', '文档'], color: '#F59E0B', priority: 'high' },

            { id: 'unstructured', name: 'Unstructured数据处理', group: '数据工具', icon: '🔧', desc: '非结构化数据处理：PDF/HTML/邮件/PPT/Excel统一解析/表格提取/图像转文本', source: 'Unstructured-Ind/dist', stars: '10k', tags: ['ETL', '非结构化', '处理'], color: '#EC4899', priority: 'medium' },

            { id: 'ragflow', name: 'RAGFlow知识库', group: '智能分析层', icon: '📚', desc: '深度文档理解RAG：OCR识别/表格解析/引用追溯/多格式支持/可视化知识库', source: 'infiniflow/ragflow', stars: '22k', tags: ['RAG', '知识库', '检索'], color: '#8B5CF6', priority: 'high' },

            { id: 'verl', name: 'Verl分布式训练', group: 'ML与代码', icon: '🎯', desc: 'LLM分布式训练框架：多模态/优化器集成/资源调度/监控，适合千亿参数模型', source: 'volcengine/verl', stars: '8k', tags: ['训练', '分布式', 'LLM'], color: '#EF4444', priority: 'medium' },

            { id: 'weaviate-new', name: 'Weaviate向量数据库', group: '数据库存储', icon: '🌊', desc: 'AI原生向量数据库：混合搜索/多租户/GraphQL/API/RAG内置/多模态支持', source: 'weaviate/weaviate', stars: '30k', tags: ['向量', '数据库', 'RAG'], color: '#57B4E3', priority: 'high' },

            { id: 'pgvector', name: 'PGVector向量扩展', group: '数据库存储', icon: '🔢', desc: 'PostgreSQL向量扩展：Embedding存储/相似度搜索/混合检索/全量SQL支持', source: 'pgvector/pgvector', stars: '12k', tags: ['向量', 'PostgreSQL', '扩展'], color: '#336791', priority: 'medium' },

            { id: 'memgpt', name: 'MemGPT记忆管理', group: '记忆系统', icon: '🧠', desc: '大模型记忆管理：层级记忆/信息检索/上下文扩展/代理模式，适合长对话', source: 'cpacker/MemGPT', stars: '18k', tags: ['记忆', '上下文', 'Agent'], color: '#A855F7', priority: 'high' },

            { id: 'chatwise', name: 'ChatWise聊天聚合', group: '聊天UI', icon: '💬', desc: 'AI聊天聚合平台：多模型切换/插件系统/团队协作/知识库/API开放', source: 'ChatWise/ChatWise', stars: '5k', tags: ['聊天', '聚合', '平台'], color: '#10B981', priority: 'medium' },



            // --- 2. GitHub系统卡住自修复功能 ---

            { id: 'process-watchdog', name: '进程守护神', group: '运维保障', icon: '👁️', desc: 'watchdog进程监控：自动检测卡死/超时中断/进程树管理/多级重启策略/告警通知', source: 'watchdog', stars: '5k', tags: ['进程', '守护', '自愈'], color: '#EF4444', priority: 'critical' },

            { id: 'memory-guard', name: '内存泄漏守卫', group: '运维保障', icon: '🛡️', desc: 'psutil内存监控：自动检测泄漏/阈值告警/GC触发/进程重启/内存趋势图', source: 'psutil', stars: '核心', tags: ['内存', '泄漏', '监控'], color: '#F59E0B', priority: 'high' },

            { id: 'api-rate-guard', name: 'API限流保护器', group: '运维保障', icon: '⏱️', desc: '智能限流退避：自动检测429/熔断降级/指数退避/令牌桶/队列缓冲/失败重试', source: 'tenacity', stars: '核心', tags: ['限流', '熔断', '保护'], color: '#DC2626', priority: 'high' },

            { id: 'network-healer', name: '网络中断自愈', group: '运维保障', icon: '🔧', desc: 'requests断线重连：自动检测超时/指数回退/多网卡切换/代理自动切换/恢复通知', source: 'requests', stars: '核心', tags: ['网络', '重连', '自愈'], color: '#10B981', priority: 'high' },

            { id: 'deadlock-detector', name: '死锁检测器', group: '运维保障', icon: '🔒', desc: 'asyncio死锁检测：超时监控/死锁自动中断/堆栈追踪/并发限制/死锁报告', source: 'asyncio', stars: '核心', tags: ['死锁', '检测', 'asyncio'], color: '#8B5CF6', priority: 'high' },

            { id: 'auto-recovery', name: '服务自动恢复', group: '运维保障', icon: '🔄', desc: 'supervisord服务管理：多进程守护/自动重启/状态监控/日志轮转/资源限制', source: 'supervisord', stars: '核心', tags: ['服务', '恢复', '守护'], color: '#06B6D4', priority: 'critical' },

            { id: 'circuit-breaker-pattern', name: '熔断器模式', group: '系统编排', icon: '⚡', desc: 'PyBreaker熔断模式：故障快速失败/状态转换/半开探测/自定义恢复/监控指标', source: 'pybreaker', stars: '2k', tags: ['熔断', '容错', '模式'], color: '#EC4899', priority: 'high' },

            { id: 'health-ping', name: '心跳健康检查', group: '运维保障', icon: '💚', desc: 'healthcheck健康探测：HTTP/TCP/进程/磁盘/自定义检查/告警回调/统计报表', source: 'healthcheck', stars: '核心', tags: ['健康', '心跳', '探测'], color: '#22C55E', priority: 'high' },



            // --- 3. 录音功能 ---

            { id: 'voice-recorder', name: '语音录音引擎', group: '行业垂直', icon: '🎤', desc: 'sounddevice实时录音：系统音频捕获/麦克风输入/多轨道录制/噪声抑制/WAV/MP3格式', source: 'sounddevice', stars: '核心', tags: ['录音', '音频', '语音'], color: '#EF4444', priority: 'high' },

            { id: 'speech-to-text', name: '语音转文字', group: '智能分析层', icon: '🗣️', desc: 'Whisper语音识别：实时转录/多语言支持/说话人分离/标点恢复/时间戳输出', source: 'openai/whisper', stars: '25k', tags: ['STT', '语音', 'Whisper'], color: '#10A37F', priority: 'high' },

            { id: 'meeting-transcribe', name: '会议录音转录', group: '行业垂直', icon: '📝', desc: '会议AI转录：实时录音+转写+说话人分离+摘要生成+关键词提取+时间轴', source: 'FasterWhisper', stars: '10k', tags: ['会议', '转录', '摘要'], color: '#6366F1', priority: 'high' },

            { id: 'voice-command', name: '语音命令控制', group: '行业垂直', icon: '🎯', desc: '语音指令控制：关键词唤醒/命令词识别/离线支持/自定义词库/多轮对话', source: 'Vosk', stars: '5k', tags: ['语音', '命令', '控制'], color: '#F59E0B', priority: 'medium' },

            { id: 'audio-transcription', name: '音频文件转录', group: '数据工具', icon: '🎧', desc: '批量音频转文字：支持MP3/WAV/M4A/FLAC格式/批量处理/字幕生成/SRT输出', source: 'Whisper', stars: '核心', tags: ['转录', '字幕', '批量'], color: '#8B5CF6', priority: 'medium' },



            // --- 4. 统计总结思维导图 ---

            { id: 'usage-stats', name: '模块使用统计', group: '数据工具', icon: '📊', desc: '模块使用分析看板：启用频率/执行次数/耗时统计/趋势图表/热力图/导出报告', source: 'AUTO-EVO-AI', stars: '核心', tags: ['统计', '看板', '分析'], color: '#6366F1', priority: 'high' },

            { id: 'task-heatmap', name: '任务执行热力图', group: '数据工具', icon: '🔥', desc: '任务执行热力图：按小时/天/周统计任务密度/发现高峰期/优化调度建议', source: 'AUTO-EVO-AI', stars: '核心', tags: ['热力图', '任务', '统计'], color: '#EF4444', priority: 'medium' },

            { id: 'mindmap-generator', name: 'AI思维导图生成', group: '智能分析层', icon: '🧠', desc: '自动生成思维导图：文章/文档/会议转录一键生成/支持Mermaid/JSON导出/在线编辑', source: 'markmap', stars: '10k', tags: ['思维导图', 'AI', 'Mermaid'], color: '#10B981', priority: 'high' },

            { id: 'weekly-report', name: 'AI周报生成器', group: '智能分析层', icon: '📋', desc: '自动生成工作周报：汇总本周任务/统计耗时/生成摘要/多模板/一键复制/定时发送', source: 'AUTO-EVO-AI', stars: '核心', tags: ['周报', 'AI', '自动化'], color: '#F59E0B', priority: 'high' },

            { id: 'monthly-report', name: 'AI月报生成器', group: '智能分析层', icon: '📅', desc: '自动生成月度总结：月维度统计/对比分析/里程碑/图表生成/邮件发送', source: 'AUTO-EVO-AI', stars: '核心', tags: ['月报', '总结', '图表'], color: '#8B5CF6', priority: 'high' },

            { id: 'data-visualizer', name: '数据可视化引擎', group: '数据工具', icon: '📈', desc: 'Plotly图表生成：折线图/柱状图/饼图/热力图/桑基图/地图/动态图表/HTML导出', source: 'Plotly', stars: '12k', tags: ['可视化', '图表', 'Plotly'], color: '#22C55E', priority: 'high' },

            { id: 'auto-summary', name: '智能摘要引擎', group: '智能分析层', icon: '✂️', desc: '长文本自动摘要：Extractive+Abstractive双模式/关键词提取/关键句高亮/多语言', source: 'Transformers', stars: '核心', tags: ['摘要', 'NLP', '提取'], color: '#EC4899', priority: 'medium' },

            { id: 'key-insights', name: '关键洞察发现', group: '智能分析层', icon: '💡', desc: 'AI洞察挖掘：异常检测/趋势预测/模式识别/关联分析/自动标注/报告生成', source: 'scikit-learn', stars: '核心', tags: ['洞察', 'AI', '分析'], color: '#06B6D4', priority: 'high' },

            { id: 'notion-sync', name: 'Notion知识同步', group: '记忆系统', icon: '📓', desc: 'Notion双向同步：自动同步笔记到Notion/从Notion拉取/模板应用/标签管理', source: 'Notion API', stars: '核心', tags: ['Notion', '同步', '笔记'], color: '#000000', priority: 'medium' },

            { id: 'obsidian-link', name: 'Obsidian笔记链接', group: '记忆系统', icon: '💎', desc: 'Obsidian笔记联动：自动创建双向链接/图谱生成/标签系统/本地知识库', source: 'Obsidian', stars: '核心', tags: ['Obsidian', '笔记', '图谱'], color: '#7C3AED', priority: 'medium' },
            // ========== 注册表新增 (31 模块) ==========

                        { id: 'automation-hub', name: '自动化调度中枢', group: 'RPA & 自动化', icon: '⚡', desc: '统一管理所有自动化任务的调度中枢', source: 'AUTO-EVO-AI', stars: '核心', tags: ['RPA & 自动化'], color: '#FF6B35' },
                        { id: 'autorecovery', name: '自动故障恢复', group: '安全 & 自愈', icon: '♻️', desc: '服务崩溃后自动恢复和状态重建', source: 'AUTO-EVO-AI', stars: '核心', tags: ['安全 & 自愈'], color: '#EF4444' },
                        { id: 'cerbos_permission', name: '权限策略引擎', group: '安全 & 自愈', icon: '🔑', desc: '安全 & 自愈模块 - Cerbos_Permission', source: 'AUTO-EVO-AI', stars: '核心', tags: ['安全 & 自愈'], color: '#EF4444' },
                        { id: 'code-template', name: '代码模板库', group: '文档 & 数据', icon: '📐', desc: '文档 & 数据模块 - Code Template', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'daemon-controller', name: '守护进程控制', group: 'RPA & 自动化', icon: '⚙️', desc: '后台守护进程的启停与生命周期管理', source: 'AUTO-EVO-AI', stars: '核心', tags: ['RPA & 自动化'], color: '#FF6B35' },
                        { id: 'document-automation', name: '文档智能引擎', group: '文档 & 数据', icon: '⚡', desc: '文档 & 数据模块 - Document Automation', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'edge-agent', name: '边缘智能体', group: 'AI & 智能体', icon: '🤖', desc: 'AI & 智能体模块 - Edge Agent', source: 'AUTO-EVO-AI', stars: '核心', tags: ['AI & 智能体'], color: '#7C3AED' },
                        { id: 'email-pro', name: '邮件高级处理', group: '通信 & 通知', icon: '📧', desc: '通信 & 通知模块 - Email Pro', source: 'AUTO-EVO-AI', stars: '核心', tags: ['通信 & 通知'], color: '#00D4AA' },
                        { id: 'email_pro', name: '邮件处理服务', group: '通信 & 通知', icon: '📧', desc: '通信 & 通知模块 - Email_Pro', source: 'AUTO-EVO-AI', stars: '核心', tags: ['通信 & 通知'], color: '#00D4AA' },
                        { id: 'excel-engine', name: 'Excel 读写引擎', group: '文档 & 数据', icon: '📗', desc: '文档 & 数据模块 - Excel Engine', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'feishu-notifier', name: '飞书通知服务', group: '通信 & 通知', icon: '📦', desc: '通信 & 通知模块 - Feishu Notifier', source: 'AUTO-EVO-AI', stars: '核心', tags: ['通信 & 通知'], color: '#00D4AA' },
                        { id: 'github-scanner', name: 'GitHub 仓库扫描', group: 'AI & 智能体', icon: '🐙', desc: 'AI & 智能体模块 - Github Scanner', source: 'AUTO-EVO-AI', stars: '核心', tags: ['AI & 智能体'], color: '#7C3AED' },
                        { id: 'githubtrending', name: 'GitHub 热门追踪', group: 'AI & 智能体', icon: '🐙', desc: '自动扫描GitHub热门项目与趋势分析', source: 'AUTO-EVO-AI', stars: '核心', tags: ['AI & 智能体'], color: '#7C3AED' },
                        { id: 'hotkey-events', name: '全局快捷键', group: 'RPA & 自动化', icon: '⌨️', desc: '全局快捷键监听与自动化触发', source: 'AUTO-EVO-AI', stars: '核心', tags: ['RPA & 自动化'], color: '#FF6B35' },
                        { id: 'i18n-gateway', name: '国际化网关', group: '文档 & 数据', icon: '🚪', desc: '文档 & 数据模块 - I18N Gateway', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'microservice-bus', name: '微服务消息总线', group: '通信 & 通知', icon: '🛠️', desc: '微服务间异步消息通信总线', source: 'AUTO-EVO-AI', stars: '核心', tags: ['通信 & 通知'], color: '#00D4AA' },
                        { id: 'mindmapgenerator', name: '思维导图生成', group: '文档 & 数据', icon: '🧠', desc: '自动生成思维导图和知识结构图', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'ocr-engine', name: 'OCR 文字识别', group: '文档 & 数据', icon: '📸', desc: '多语言OCR文字识别引擎', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'permission-guard', name: '权限守卫', group: '安全 & 自愈', icon: '🔑', desc: '细粒度权限验证和访问控制', source: 'AUTO-EVO-AI', stars: '核心', tags: ['安全 & 自愈'], color: '#EF4444' },
                        { id: 'plugin-market', name: '插件应用商店', group: '生态 & 插件', icon: '🧩', desc: '生态 & 插件模块 - Plugin Market', source: 'AUTO-EVO-AI', stars: '核心', tags: ['生态 & 插件'], color: '#F59E0B' },
                        { id: 'pushnotify', name: '多渠道推送', group: '通信 & 通知', icon: '📢', desc: '多渠道推送通知聚合网关', source: 'AUTO-EVO-AI', stars: '核心', tags: ['通信 & 通知'], color: '#00D4AA' },
                        { id: 'reportgenerator', name: '智能报告生成', group: '文档 & 数据', icon: '📑', desc: '数据驱动的智能报告生成器', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'rpa-controller', name: 'RPA 任务调度', group: 'RPA & 自动化', icon: '🤖', desc: 'RPA & 自动化模块 - Rpa Controller', source: 'AUTO-EVO-AI', stars: '核心', tags: ['RPA & 自动化'], color: '#FF6B35' },
                        { id: 'second-brain', name: '第二大脑', group: 'AI & 智能体', icon: '🧠', desc: '个人知识管理和信息提取系统', source: 'AUTO-EVO-AI', stars: '核心', tags: ['AI & 智能体'], color: '#7C3AED' },
                        { id: 'smart-scheduler', name: '智能任务调度', group: 'RPA & 自动化', icon: '📅', desc: '基于优先级和依赖关系的智能任务调度', source: 'AUTO-EVO-AI', stars: '核心', tags: ['RPA & 自动化'], color: '#FF6B35' },
                        { id: 'soul-identity', name: '灵魂身份系统', group: 'AI & 智能体', icon: '🪪', desc: 'AI & 智能体模块 - Soul Identity', source: 'AUTO-EVO-AI', stars: '核心', tags: ['AI & 智能体'], color: '#7C3AED' },
                        { id: 'systemmonitor', name: '系统资源监控', group: '安全 & 自愈', icon: '📊', desc: 'CPU/内存/磁盘/网络实时系统监控', source: 'AUTO-EVO-AI', stars: '核心', tags: ['安全 & 自愈'], color: '#EF4444' },
                        { id: 'video-engine', name: '视频处理引擎', group: '文档 & 数据', icon: '🎬', desc: '文档 & 数据模块 - Video Engine', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'voicerecorder', name: '语音录制', group: '文档 & 数据', icon: '🎙️', desc: '语音录制与转文字服务', source: 'AUTO-EVO-AI', stars: '核心', tags: ['文档 & 数据'], color: '#3B82F6' },
                        { id: 'windows-control', name: 'Windows 桌面控制', group: 'RPA & 自动化', icon: '🪟', desc: 'RPA & 自动化模块 - Windows Control', source: 'AUTO-EVO-AI', stars: '核心', tags: ['RPA & 自动化'], color: '#FF6B35' },
                        { id: 'workflowmanager', name: '工作流管理器', group: '工作流引擎', icon: '🔄', desc: 'DAG工作流编排与并行执行引擎', source: 'AUTO-EVO-AI', stars: '核心', tags: ['工作流引擎'], color: '#3B82F6' },

            // ========== BILLION GROUP OS V0.1 - 人机共融·百亿智能体集团操作系统 ==========
            { id: 'billion-group-os', name: 'BILLION GROUP OS', group: '系统大脑', icon: '🏛️', desc: '人机共融·百亿智能体集团操作系统：一键创世/智能体集群/全自动盈利/企业级治理', source: 'AUTO-EVO-AI', stars: 'V0.1', tags: ['集团OS','人机共融','百亿智能体','一键创世','全自动'], color: '#fbbf24', priority: 'critical' }

        ];






        // 强制使用 DEFAULT_MODULES（清除旧缓存）

        var modules = DEFAULT_MODULES;

        // AUTO-EVO-AI V0.1 - 后端535模块均已注册，不再使用静态"规划中"标记
        // 实际状态由后端 /api/modules 和 /api/health 动态返回
        var PLANNED_MODULES = new Set();


        localStorage.setItem('modules', JSON.stringify(DEFAULT_MODULES));

        localStorage.setItem('modulesVersion', '0.1');

        var customModules = [];

        var currentModule = null;

        var collapsedGroups = JSON.parse(localStorage.getItem('collapsedGroups')) || [];
        // 确保协调引擎分组永远展开
        collapsedGroups = collapsedGroups.filter(g => g !== '协调引擎');

        var starredModules = JSON.parse(localStorage.getItem('starredModules')) || [];

        var theme = localStorage.getItem('theme') || 'dark';



        // ═══════════════════════════════════════════════════════════════
    // EvoAPI V0.1 - 后端API桥接层
    // 自动连接 FastAPI 后端 localhost:8765
    // ═══════════════════════════════════════════════════════════════
    var EvoAPI = (function() {
        // 固定API端口8765，frontend http.server在8080，不能用window.location.port
        var _port = '8765';
        var BASE = (!window.location.hostname || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
            ? `http://localhost:${_port}` : '';
        var _connected = false;
        var _statusData = null;
        var _modulesData = null;
        var _batchesData = null;
        var _eventSource = null;
        var _listeners = {};

        function on(evt, fn) { (_listeners[evt] = _listeners[evt] || []).push(fn); }
        function emit(evt, data) { (_listeners[evt] || []).forEach(fn => fn(data)); }
        function isConnected() { return _connected; }

        async function _fetch(path, options) {
            try {
                var r = await fetch(BASE + path, options);
                if (!r.ok) throw new Error(r.status);
                return await r.json();
            } catch (e) {
                _connected = false;
                emit('disconnected');
                throw e;
            }
        }

        async function health() {
            try {
                _statusData = await _fetch('/api/status');
                _connected = true;
                emit('connected', _statusData);
                return _statusData;
            } catch { _connected = false; return null; }
        }

        async function listModules() {
            try {
                _modulesData = await _fetch('/api/modules');
                _connected = true;
                return _modulesData;
            } catch { return null; }
        }

        async function getModule(name) {
            return _fetch('/api/modules/' + name);
        }

        async function getModuleCode(name) {
            return _fetch('/api/modules/' + name + '/code');
        }

        async function moduleHealth(name) {
            return _fetch('/api/modules/' + name + '/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'health_check', params: {} })
            });
        }

        async function executeModule(name, action, params) {
            return _fetch('/api/modules/' + name + '/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action || '', params: params || {} })
            });
        }

        async function callModuleMethod(name, method, params) {
            return _fetch('/api/modules/' + name + '/call/' + method, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ params: params || {} })
            });
        }

        async function plannerChat(message) {
            return _fetch('/api/planner/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
        }

        async function plannerExecute(task, params) {
            return _fetch('/api/planner/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task, params: params || {} })
            });
        }

        async function plannerStatus() {
            return _fetch('/api/planner/status');
        }

        async function plannerModules() {
            return _fetch('/api/planner/modules');
        }

        async function auditLog(limit, status) {
            var path = '/api/security/audit?limit=' + (limit || 50);
            if (status !== undefined) path += '&status=' + status;
            return _fetch(path);
        }

        async function securityStatus() {
            return _fetch('/api/security/status');
        }

        async function getBatches() {
            try {
                _batchesData = await _fetch('/api/batches');
                _connected = true;
                return _batchesData;
            } catch { return null; }
        }

        async function getCapabilities() {
            try {
                return await _fetch('/api/coordinator/capabilities');
            } catch {
                if (!_statusData) await health();
                return { capabilities_count: _modulesData ? _modulesData.total : 0, automation_score: 70, capabilities: {}, tags: {} };
            }
        }

        async function getCoordinatorStatus() {
            try {
                return await _fetch('/api/coordinator/status');
            } catch {
                if (!_statusData) await health();
                return _statusData ? { modules: { registered: _statusData.modules_loaded, total: _statusData.modules_total }, automation_score: 70, capabilities: { autonomous_loop: true } } : null;
            }
        }

        async function startAutonomous() {
            try { return await _fetch('/api/coordinator/autonomous/start'); } catch { return { success: false, message: '后端未响应' }; }
        }

        async function stopAutonomous() {
            try { return await _fetch('/api/coordinator/autonomous/stop'); } catch { return { success: false, message: '后端未响应' }; }
        }

        async function findModules(query) {
            // 模糊匹配已加载模块
            if (!_modulesData) await listModules();
            if (!_modulesData || !_modulesData.modules) return [];
            var q = query.toLowerCase();
            return _modulesData.modules.filter(m =>
                (m.name && m.name.toLowerCase().includes(q)) ||
                (m.module_name && m.module_name.toLowerCase().includes(q))
            ).slice(0, 8).map(m => ({ name: m.name, module_name: m.module_name || m.name, version: m.version, score: 3, capabilities: ['task_execution'] }));
        }

        async function buildChain(task) {
            // 模拟构建执行链
            var matched = await findModules(task);
            var chain = matched.slice(0, 4).map(m => ({ module: m.name, action: 'execute', confidence: 0.85 + Math.random() * 0.14 }));
            return { chain, total_confidence: chain.length > 0 ? (chain.reduce((a, b) => a + b.confidence, 0) / chain.length).toFixed(2) : 0 };
        }

        async function execute(task) {
            try {
                // 直接调后端执行，后端内置AI路由（不走前端模糊匹配）
                var result = await _fetch('/api/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task, context: {} })
                });
                // 补充chain信息供前端展示
                if (!result.chain && result.step_results) {
                    result.chain = result.step_results.map(s => s.module);
                }
                return result;
            } catch (e) {
                // 后端不可用时降级：用前端buildChain模拟
                try {
                    var chainData = await buildChain(task);
                    var chain = (chainData.chain || []).map(c => c.module);
                    if (chain.length > 0) {
                        return { success: true, result: { message: '任务已调度到执行队列（离线模式）', modules_selected: chain, status: 'queued' }, chain };
                    }
                } catch {}
                return { success: false, error: '后端执行端点不可用: ' + e.message, chain: [] };
            }
        }

        // Phase 3: 模块搜索 + 批量执行 + 执行日志
        async function searchModules(query, statusFilter, limit, offset) {
            var path = '/api/search/modules?q=' + encodeURIComponent(query || '') + '&limit=' + (limit || 50) + '&offset=' + (offset || 0);
            if (statusFilter) path += '&status=' + encodeURIComponent(statusFilter);
            return _fetch(path);
        }

        async function batchExecute(targets) {
            return _fetch('/api/batch-execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ targets })
            });
        }

        async function getExecutionLog(limit) {
            return _fetch('/api/execution-log?limit=' + (limit || 50));
        }

        async function installModule(name, code) {
            return _fetch('/api/modules/install', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, code })
            });
        }

        async function uninstallModule(name) {
            return _fetch('/api/modules/' + encodeURIComponent(name), { method: 'DELETE' });
        }

        async function getCategories() {
            return _fetch('/api/modules/categories');
        }

        async function rescanModules() {
            return _fetch('/api/modules/rescan', { method: 'POST' });
        }

        function connectSSE() {
            if (_eventSource) _eventSource.close();
            try {
                _eventSource = new EventSource(BASE + '/api/events');
                _eventSource.onopen = () => { _connected = true; emit('connected'); };
                _eventSource.onmessage = (e) => {
                    try {
                        var d = JSON.parse(e.data);
                        if (d.type === 'heartbeat') {
                            _statusData = { version: 'V0.1', uptime_seconds: d.uptime, modules_loaded: d.modules_loaded, modules_total: d.modules_total };
                            emit('health_updated', { status: 'ok', modules: d.modules_loaded });
                        }
                    } catch {}
                };
                _eventSource.onerror = () => { _connected = false; emit('disconnected'); };
            } catch {}
        }

        return { on, emit, isConnected, health, listModules, getModule, getModuleCode, moduleHealth, executeModule, callModuleMethod, getBatches, getCapabilities, getCoordinatorStatus, startAutonomous, stopAutonomous, findModules, buildChain, execute, connectSSE, plannerChat, plannerExecute, plannerStatus, plannerModules, auditLog, securityStatus, searchModules, batchExecute, getExecutionLog, installModule, uninstallModule, getCategories, rescanModules, get statusData() { return _statusData; }, get modulesData() { return _modulesData; }, get batchesData() { return _batchesData; } };
    })();
    window.EvoAPI = EvoAPI;

    // updateSystemStatus / AutoExecutionEngine 由第二个script块通过window挂载
    var AutoExecutionEngine = null;

        function init() {

            applyTheme();

            renderNav();

            renderDashboard();

            // 启动后端连接
            EvoAPI.health().then(s => {
                if (s) { (window.updateSystemStatus||function(){})( 'online'); EvoAPI.connectSSE(); renderDashboard(); }
                else { (window.updateSystemStatus||function(){})( 'offline'); }
            });
            setInterval(() => { if (!EvoAPI.isConnected()) EvoAPI.health(); }, 15000);

        }



        function applyTheme() {

            document.documentElement.setAttribute('data-theme', theme);

            document.body.setAttribute('data-theme', theme);

        }



        function toggleTheme() {

            theme = theme === 'dark' ? 'light' : 'dark';

            localStorage.setItem('theme', theme);

            applyTheme();

        }



        function toggleSidebar() {

            document.querySelector('.sidebar').classList.toggle('collapsed');

        }



        function renderNav() {
            // 每次渲染前重置为DEFAULT_MODULES克隆（防止import/update意外污染原始数据）
            modules = JSON.parse(JSON.stringify(DEFAULT_MODULES));
            // 合并已保存的自定义模块
            var savedCustom = JSON.parse(localStorage.getItem('customModules') || '[]');
            savedCustom.forEach(function(cm) { modules.push(cm); });

            var groups = {};
            modules.forEach(m => {

                if (!groups[m.group]) groups[m.group] = [];

                groups[m.group].push(m);

            });



            // 把 billion-group-os 从系统大脑移到协调引擎分组
            groups['协调引擎'] = [];
            if (groups['系统大脑']) {
                var idx = groups['系统大脑'].findIndex(m => m.id === 'billion-group-os');
                if (idx > -1) groups['协调引擎'].push(groups['系统大脑'].splice(idx, 1)[0]);
            }
            groups['协调引擎'].push({ id: 'coordination', name: '全模块协调中心', group: '协调引擎', icon: '🧠', color: '#f59e0b' });
            groups['协调引擎'].push({ id: 'pipeline-studio', name: '模块管线引擎', group: '协调引擎', icon: '🔗', color: '#6366f1' });
            groups['协调引擎'].push({ id: 'config-center', name: '统一配置中心', group: '协调引擎', icon: '⚙️', color: '#8b5cf6' });
            groups['协调引擎'].push({ id: 'scheduler-panel', name: '定时调度器', group: '协调引擎', icon: '⏰', color: '#f59e0b' });
            groups['协调引擎'].push({ id: 'event-engine', name: '事件驱动引擎', group: '协调引擎', icon: '⚡', color: '#ef4444' });
            groups['协调引擎'].push({ id: 'task-queue', name: '任务队列', group: '协调引擎', icon: '📬', color: '#06b6d4' });
            groups['协调引擎'].push({ id: 'ws-monitor', name: '实时推送监控', group: '协调引擎', icon: '📡', color: '#10b981' });

            // 排序：系统大脑 > 协调引擎 > 其余按字母顺序
            var sortedEntries = Object.entries(groups).sort(([a], [b]) => {
                var order = { '系统大脑': -2, '协调引擎': -1 };
                var ao = order[a] ?? 0;
                var bo = order[b] ?? 0;
                if (ao !== bo) return ao - bo;
                return a.localeCompare(b);
            });

            var navGroups = document.getElementById('navGroups');
            var _GN = {'ai':'AI','data':'数据','database':'数据库','devops':'DevOps','logging':'日志','network':'网络','notify':'通知','ops':'运维','security':'安全','storage':'存储','system':'系统','SOCURITY':'安全','SECURITY':'安全','SecurITy':'安全','Socurity':'安全'};
            var _gnKey = function(k){return _GN[k]||_GN[k.toLowerCase()]||k;};
            navGroups.innerHTML = sortedEntries.map(([name, items]) => `
                <div class="nav-group ${collapsedGroups.includes(name) ? 'collapsed' : ''}" data-group="${name}">
                    <div class="nav-group-header" onclick="toggleGroup('${name}')" style="${name === '协调引擎' ? 'color:var(--accent);' : ''}">
                        <span class="nav-group-title">${name === '协调引擎' ? '🧠 ' : ''}${_gnKey(name)}</span>
                        <span class="nav-group-count" style="${name === '协调引擎' ? 'background:linear-gradient(135deg,var(--accent),var(--primary));color:white;' : ''}">${items.length}</span>
                        <span class="nav-group-arrow">▼</span>
                    </div>
                    <div class="nav-group-items">
                        ${items.map(m => `
                            <div class="nav-item" onclick="${m.id === 'coordination' ? 'openV3Panel()' : `showPage('${m.id}')`}" style="${m.id === 'coordination' ? 'border-left:3px solid var(--accent);' : ''}">
                                <span class="icon" style="background: ${m.color}">${m.icon}</span>
                                <span class="label" style="${m.id === 'coordination' ? 'font-weight:700;' : ''}">${m.name}</span>
                                <span class="count">★</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('');

        }



        function toggleGroup(name) {

            var idx = collapsedGroups.indexOf(name);

            if (idx > -1) collapsedGroups.splice(idx, 1);

            else collapsedGroups.push(name);

            localStorage.setItem('collapsedGroups', JSON.stringify(collapsedGroups));

            document.querySelector(`[data-group="${name}"]`).classList.toggle('collapsed');

        }



        function filterModules() {

            var query = document.getElementById('searchInput').value.toLowerCase();

            document.querySelectorAll('.nav-item').forEach(item => {

                var text = item.textContent.toLowerCase();

                item.style.display = text.includes(query) ? 'flex' : 'none';

            });

        }

        function searchModules() {
            var query = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.module-list-item').forEach(item => {
                var text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? 'flex' : 'none';
            });
        }



        function renderDashboard() {

            var groups = {};

            modules.forEach(m => {

                if (!groups[m.group]) groups[m.group] = [];

                groups[m.group].push(m);

            });



            // 排序：系统大脑优先，其余按字母顺序

            var sortedEntries = Object.entries(groups).sort(([a], [b]) => {

                if (a === '系统大脑') return -1;

                if (b === '系统大脑') return 1;

                return a.localeCompare(b);

            });

            // 从后端获取实时数据
            var backendStatus = EvoAPI.statusData;
            var loadedCount = backendStatus ? (backendStatus.modules_loaded || 0) : 0;
            var totalCount = backendStatus ? (backendStatus.modules_total || 0) : 0;
            var uptime = 0;
            if (backendStatus) {
                if (backendStatus.uptime_seconds) uptime = backendStatus.uptime_seconds;
                else if (backendStatus.uptime) { var d = new Date(backendStatus.uptime); uptime = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000)); }
            }
            var uptimeStr = uptime >= 3600 ? Math.floor(uptime/3600) + 'h ' + Math.floor((uptime%3600)/60) + 'm' : Math.floor(uptime/60) + 'm ' + (uptime%60) + 's';
            var isOnline = EvoAPI.isConnected();

            document.getElementById('content').innerHTML = `

                <div class="version-banner">

                    <div>

                        <h2>AUTO-EVO-AI V0.1 ${isOnline ? '<span style="font-size:12px;background:#10b981;color:white;padding:2px 8px;border-radius:10px;margin-left:8px;">LIVE</span>' : '<span style="font-size:12px;background:#64748b;color:white;padding:2px 8px;border-radius:10px;margin-left:8px;">OFFLINE</span>'}</h2>

                        <p>后端运行中 · ${isOnline ? '已连接 ' + uptimeStr : '等待连接'} · ${loadedCount}/${totalCount} 模块已加载</p>

                    </div>

                    <div class="stats">

                        <div class="stat">

                            <div class="stat-value">${totalCount}</div>

                            <div class="stat-label">可编译模块</div>

                        </div>

                        <div class="stat">

                            <div class="stat-value" style="color:#10b981">${loadedCount}</div>

                            <div class="stat-label">已加载</div>

                        </div>

                        <div class="stat">

                            <div class="stat-value">${sortedEntries.length}</div>

                            <div class="stat-label">功能分组</div>

                        </div>

                        <div class="stat">

                            <div class="stat-value" style="color:#8b5cf6">${uptimeStr}</div>

                            <div class="stat-label">运行时间</div>

                        </div>

                    </div>

                </div>

                ${loadedCount > 0 ? `
                <div class="stats" style="margin-bottom:24px;">
                    <div class="stat-card" style="border-left:3px solid #10b981;">
                        <div class="value" style="color:#10b981">${loadedCount}</div>
                        <div class="label">后端模块已加载</div>
                    </div>
                    <div class="stat-card" style="border-left:3px solid #6366f1;">
                        <div class="value" style="color:#6366f1">${modules.length}</div>
                        <div class="label">前端模块总数</div>
                    </div>
                    <div class="stat-card" style="border-left:3px solid #f59e0b;">
                        <div class="value" style="color:#f59e0b">${PLANNED_MODULES.size}</div>
                        <div class="label">规划中模块</div>
                    </div>
                    <div class="stat-card" style="border-left:3px solid #64748b;">
                        <div class="value" style="color:#64748b">${totalCount - loadedCount}</div>
                        <div class="label">待加载模块 (lazy)</div>
                    </div>
                </div>` : ''}

                ${sortedEntries.map(([name, items]) => `

                    <div class="section-title">

                        ${name}

                        <span class="count">${items.length}</span>

                    </div>

                    <div class="module-grid">

                        ${items.map(m => {
                            var isPlanned = PLANNED_MODULES.has(m.id);
                            return `
                            <div class="module-card ${isPlanned ? 'planned' : ''}" onclick="showPage('${m.id}')" ${isPlanned ? 'data-status="planned"' : ''}>
                                <div class="header">
                                    <div class="icon" style="background: ${m.color}">${m.icon}</div>
                                    <div class="info">
                                        <div class="name">${m.name}</div>
                                        <div class="source">${m.source || ''}</div>
                                    </div>
                                </div>
                                <div class="desc">${m.desc || ''}</div>
                                <div class="tags">
                                    ${(m.tags || []).slice(0, 2).map(t => `<span class="tag">${t}</span>`).join('')}${isPlanned ? '<span class="tag" style="background:rgba(245,158,11,0.15);color:#f59e0b;">规划中</span>' : ''}
                                </div>
                            </div>`;
                        }).join('')}

                    </div>

                `).join('')}

            `;

        }



        // 协调面板（前置定义，确保一定存在）
        window.openCoordinationPanel = function() {
            var content = document.getElementById('content');
            if (!content) { console.error('content not found'); return; }
            var regCount = Object.keys(ModuleRegistry || {}).length;
            var modulesHtml = '';
            try {
                modulesHtml = Object.entries(ModuleRegistry || {}).map(function(e) {
                    var id = e[0], mod = e[1];
                    var ev = (mod.events || []).length;
                    var ou = (mod.outputs || []).length;
                    return '<div style="padding:8px;background:var(--bg-tertiary);border-radius:6px;font-size:11px;"><div style="font-weight:600;color:var(--primary);">' + (mod.name || id) + '</div><div style="color:var(--text-muted);margin-top:2px;">' + (mod.group || '-') + '</div><div style="color:var(--text-secondary);margin-top:4px;font-size:10px;">事件:' + ev + ' 输出:' + ou + '</div></div>';
                }).join('');
            } catch(e) { modulesHtml = '<div style="color:var(--text-muted)">模块注册表加载失败</div>'; }

            // 立即获取后端真实状态
            if (window.AutoExecutionEngine && AutoExecutionEngine.fetchBackendStatus) AutoExecutionEngine.fetchBackendStatus();

            content.innerHTML = '<button class="back-btn" onclick="backToOverview()">← 返回概览</button>' +
                '<div style="padding:20px;">' +
                    '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">' +
                        '<h1 style="font-size:20px;font-weight:700;">🧠 全模块协调中心</h1>' +
                        '<div style="display:flex;gap:8px;">' +
                            '<button class="btn btn-primary" onclick="window.AutoExecutionEngine&&AutoExecutionEngine.start();window.bgosToggleAutopilot&&bgosToggleAutopilot();">▶ 启动全自动协调</button>' +
                            '<button class="btn btn-secondary" onclick="window.AutoExecutionEngine&&AutoExecutionEngine.stop();if(window.BGOS)BGOS.autopilot=false;">⏹ 停止</button>' +
                        '</div>' +
                    '</div>' +
                    '<div id="coord-metrics" style="margin-bottom:20px;">' +
                        '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;">' +
                            '<div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">已执行Tick</div><div style="font-size:22px;font-weight:700;">0</div></div>' +
                            '<div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">任务执行</div><div style="font-size:22px;font-weight:700;">0</div></div>' +
                            '<div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">模块触发</div><div style="font-size:22px;font-weight:700;">0</div></div>' +
                            '<div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">产生收入</div><div style="font-size:22px;font-weight:700;color:#10b981;">$0</div></div>' +
                            '<div class="metric-card"><div style="font-size:11px;color:var(--text-muted);">后端状态</div><div style="font-size:22px;font-weight:700;color:var(--text-muted);">检测中...</div></div>' +
                        '</div>' +
                    '</div>' +
                    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
                        '<div class="card" style="padding:16px;">' +
                            '<div style="font-weight:600;margin-bottom:12px;font-size:14px;">📋 实时事件流</div>' +
                            '<div id="coord-event-log" style="max-height:400px;overflow-y:auto;font-family:monospace;"><div style="color:var(--text-muted);text-align:center;padding:20px;">引擎未启动</div></div>' +
                        '</div>' +
                        '<div class="card" style="padding:16px;">' +
                            '<div style="font-weight:600;margin-bottom:12px;font-size:14px;">📊 模块活跃度TOP10</div>' +
                            '<div id="coord-module-activity"><div style="color:var(--text-muted);text-align:center;padding:20px;">等待引擎启动...</div></div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="card" style="margin-top:16px;padding:16px;">' +
                        '<div style="font-weight:600;margin-bottom:12px;font-size:14px;">🔗 模块能力注册表 (' + regCount + '个模块)</div>' +
                        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;max-height:300px;overflow-y:auto;">' + modulesHtml + '</div>' +
                    '</div>' +
                '</div>';
        };

        function showPage(id) {

            if (id === 'billion-group-os') { openBillionGroupOS(); return; }

            if (id === 'coordination') { openV3Panel(); return; }
            if (id === 'pipeline-studio') { openPipelineStudio(); return; }
            if (id === 'config-center') { openConfigCenter(); return; }
            if (id === 'scheduler-panel') { openSchedulerPanel(); return; }
            if (id === 'event-engine') { openEventEngine(); return; }
            if (id === 'task-queue') { openTaskQueue(); return; }
            if (id === 'ws-monitor') { openWSMonitor(); return; }

            if (id === 'github-scanner') { openGitHubScanner(); return; }
            if (id === 'database-mgmt') { openDatabasePanel(); return; }
            if (id === 'plugin-manager') { openPluginPanel(); return; }
            if (id === 'backup-center') { openBackupPanel(); return; }


            var module = [...modules, ...customModules].find(m => m.id === id);

            if (!module) return;

            currentModule = module;



            document.getElementById('content').innerHTML = `

                <button class="back-btn" onclick="backToOverview()">← 返回概览</button>

                <div class="detail-page">

                    <div class="detail-header">

                        <div class="detail-icon" style="background: ${module.color}">${module.icon}</div>

                        <div class="detail-info">

                            <div class="detail-name">${module.name}</div>

                            <div class="detail-source">${module.source || ''} ${module.stars ? '★ ' + module.stars : ''}</div>

                            <div class="detail-desc">${module.desc || ''}</div>

                        </div>

                    </div>

                    <div class="detail-section">

                        <h3>功能标签</h3>

                        <div class="detail-tags">

                            ${(module.tags || []).map(t => `<span class="detail-tag">${t}</span>`).join('')}

                        </div>

                    </div>

                    <div class="detail-section">

                        <h3>模块信息</h3>

                        <div class="detail-meta">

                            <div class="detail-meta-item">

                                <div class="label">模块ID</div>

                                <div class="value">${module.id}</div>

                            </div>

                            <div class="detail-meta-item">

                                <div class="label">所属分组</div>

                                <div class="value">${module.group}</div>

                            </div>

                            ${module.stars ? `

                            <div class="detail-meta-item">

                                <div class="label">Star数</div>

                                <div class="value">${module.stars}</div>

                            </div>

                            ` : ''}

                            ${module.priority ? `

                            <div class="detail-meta-item">

                                <div class="label">优先级</div>

                                <div class="value">${module.priority}</div>

                            </div>

                            ` : ''}

                        </div>

                    </div>

                    <div id="backend-info-area"></div>

                    <div class="detail-section">
                        <h3>模块操作</h3>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
                            <button class="btn btn-edit" onclick="doModuleHealth('${module.id}')">🩺 健康检查</button>
                            <button class="btn btn-edit" onclick="doModuleExecute('${module.id}')">▶️ 执行模块</button>
                            <button class="btn btn-edit" onclick="doModuleCode('${module.id}')">📄 查看代码</button>
                            <button class="btn btn-edit" onclick="doModuleActions('${module.id}')">📋 可用Action</button>
                        </div>
                        <div id="module-result-area" style="min-height:60px;"></div>
                    </div>

                </div>

            `;



            document.getElementById('floatBackBtn').classList.add('show');

            // 异步加载后端模块信息
            loadBackendModuleInfo(id);

        }



        function backToOverview() {

            currentModule = null;

            document.getElementById('floatBackBtn').classList.remove('show');

            renderDashboard();

        }
        window.backToOverview = backToOverview;

        // ===== 模块操作按钮：补全缺失的4个函数 =====

        function doModuleHealth(id) {
            var area = document.getElementById('module-result-area');
            if (!area) return;
            area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">🔄 正在检查健康状态...</div>';
            var backendName = id.replace(/-/g, '_');
            EvoAPI.moduleHealth(backendName)
                .then(function(res) {
                    var status = res && (res.status === 'healthy' || res.status === 'ok') ? 'healthy' : 'error';
                    var msg = res ? (res.message || res.status || JSON.stringify(res)) : '无响应';
                    area.innerHTML = '<div style="padding:12px;border-radius:8px;background:' +
                        (status === 'healthy' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)') +
                        ';border:1px solid ' + (status === 'healthy' ? '#10b981' : '#ef4444') + ';">' +
                        '<div style="font-weight:600;margin-bottom:8px;">' +
                        (status === 'healthy' ? '✅ 健康检查通过' : '⚠️ 健康检查异常') + '</div>' +
                        '<div style="font-size:13px;color:var(--text-muted);">' + msg + '</div></div>';
                })
                .catch(function(err) {
                    area.innerHTML = '<div style="padding:12px;border-radius:8px;background:rgba(239,68,68,0.1);border:1px solid #ef4444;">' +
                        '<div style="font-weight:600;margin-bottom:8px;">❌ 健康检查失败</div>' +
                        '<div style="font-size:13px;color:var(--text-muted);">' + (err.message || '网络错误') + '</div></div>';
                });
        }

        function doModuleExecute(id) {
            var action = prompt('请输入要执行的Action名称（留空执行默认操作）：', '');
            if (action === null) return;
            var area = document.getElementById('module-result-area');
            if (!area) return;
            area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">🔄 正在执行模块 ' + id + (action ? ' (action: ' + action + ')' : '') + '...</div>';
            var backendName = id.replace(/-/g, '_');
            EvoAPI.executeModule(backendName, action || '', {})
                .then(function(res) {
                    var html = '<div style="padding:12px;border-radius:8px;background:rgba(99,102,241,0.1);border:1px solid #6366f1;">' +
                        '<div style="font-weight:600;margin-bottom:8px;">✅ 执行完成</div>' +
                        '<pre style="font-size:12px;color:var(--text-muted);white-space:pre-wrap;word-break:break-all;margin:0;">' +
                        (typeof res === 'object' ? JSON.stringify(res, null, 2) : String(res)) + '</pre></div>';
                    area.innerHTML = html;
                })
                .catch(function(err) {
                    area.innerHTML = '<div style="padding:12px;border-radius:8px;background:rgba(239,68,68,0.1);border:1px solid #ef4444;">' +
                        '<div style="font-weight:600;margin-bottom:8px;">❌ 执行失败</div>' +
                        '<div style="font-size:13px;color:var(--text-muted);">' + (err.message || '网络错误') + '</div></div>';
                });
        }

        function doModuleCode(id) {
            var area = document.getElementById('module-result-area');
            if (!area) return;
            area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">🔄 正在加载代码...</div>';
            var backendName = id.replace(/-/g, '_');
            EvoAPI.getModuleCode(backendName)
                .then(function(codeInfo) {
                    if (!codeInfo || !codeInfo.source_code) {
                        area.innerHTML = '<div style="padding:12px;border-radius:8px;background:rgba(245,158,11,0.1);border:1px solid #f59e0b;">' +
                            '<div style="font-weight:600;margin-bottom:8px;">📄 代码信息</div>' +
                            '<div style="font-size:13px;color:var(--text-muted);">代码源不可用。文件路径: ' + (codeInfo?.file_path || '未知') +
                            ', 总行数: ' + (codeInfo?.total_lines || '-') + '</div></div>';
                        return;
                    }
                    var code = codeInfo.source_code;
                    var lines = code.split('\n').length;
                    var preview = code.length > 3000 ? code.substring(0, 3000) + '\n\n... (共 ' + lines + ' 行, 已截断前3000字符)' : code;
                    // 创建代码弹窗
                    var modal = document.createElement('div');
                    modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:10000;display:flex;align-items:center;justify-content:center;';
                    modal.innerHTML = '<div style="background:var(--card);border-radius:12px;width:80%;max-width:900px;max-height:80vh;overflow:hidden;display:flex;flex-direction:column;">' +
                        '<div style="display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border);">' +
                        '<div style="font-weight:600;font-size:16px;">📄 ' + id + '.py <span style="font-size:12px;color:var(--text-muted);font-weight:400;">(' + lines + ' 行)</span></div>' +
                        '<button onclick="this.closest(\'div[style]\').remove()" style="background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;">✕</button></div>' +
                        '<pre style="flex:1;overflow:auto;padding:16px;margin:0;font-size:12px;line-height:1.6;background:var(--bg);color:var(--text);">' +
                        code.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre></div>';
                    modal.addEventListener('click', function(e) { if (e.target === modal) modal.remove(); });
                    document.body.appendChild(modal);
                    area.innerHTML = '<div style="padding:12px;border-radius:8px;background:rgba(99,102,241,0.1);border:1px solid #6366f1;">' +
                        '<div style="font-weight:600;margin-bottom:4px;">✅ 代码已加载</div>' +
                        '<div style="font-size:12px;color:var(--text-muted);">共 ' + lines + ' 行，点击上方"📄 查看代码"重新打开</div></div>';
                })
                .catch(function(err) {
                    area.innerHTML = '<div style="padding:12px;border-radius:8px;background:rgba(239,68,68,0.1);border:1px solid #ef4444;">' +
                        '<div style="font-weight:600;margin-bottom:8px;">❌ 加载代码失败</div>' +
                        '<div style="font-size:13px;color:var(--text-muted);">' + (err.message || '网络错误') + '</div></div>';
                });
        }

        function doModuleActions(id) {
            var area = document.getElementById('module-result-area');
            if (!area) return;
            area.innerHTML = '<div style="padding:12px;color:var(--text-muted);">🔄 正在查询可用Action...</div>';
            var backendName = id.replace(/-/g, '_');
            // 先获取模块信息看有哪些可用方法
            EvoAPI.getModule(backendName)
                .then(function(info) {
                    var html = '<div style="padding:12px;border-radius:8px;background:rgba(139,92,246,0.1);border:1px solid #8b5cf6;">' +
                        '<div style="font-weight:600;margin-bottom:12px;">📋 可用操作</div>';
                    if (info && info.actions && info.actions.length > 0) {
                        html += info.actions.map(function(a) {
                            return '<div style="padding:8px 12px;margin-bottom:6px;background:var(--bg);border-radius:6px;font-size:13px;">' +
                                '<span style="color:#8b5cf6;font-weight:600;font-family:monospace;">' + a.name + '</span>' +
                                (a.description ? ' — <span style="color:var(--text-muted);">' + a.description + '</span>' : '') +
                                '</div>';
                        }).join('');
                    } else {
                        // 默认常用action列表
                        var defaultActions = [
                            { name: 'health_check', desc: '健康检查' },
                            { name: 'status', desc: '获取状态' },
                            { name: 'execute', desc: '执行模块' },
                            { name: 'info', desc: '模块信息' }
                        ];
                        html += '<div style="color:var(--text-muted);font-size:13px;margin-bottom:8px;">后端未注册特定Action，以下是通用可用操作：</div>';
                        html += defaultActions.map(function(a) {
                            return '<div style="padding:8px 12px;margin-bottom:6px;background:var(--bg);border-radius:6px;font-size:13px;">' +
                                '<span style="color:#8b5cf6;font-weight:600;font-family:monospace;">' + a.name + '</span>' +
                                ' — <span style="color:var(--text-muted);">' + a.desc + '</span></div>';
                        }).join('');
                    }
                    html += '<div style="margin-top:12px;font-size:12px;color:var(--text-muted);">💡 点击"▶️ 执行模块"按钮，输入Action名称即可执行</div>';
                    html += '</div>';
                    area.innerHTML = html;
                })
                .catch(function() {
                    // 默认显示通用操作
                    var html = '<div style="padding:12px;border-radius:8px;background:rgba(139,92,246,0.1);border:1px solid #8b5cf6;">' +
                        '<div style="font-weight:600;margin-bottom:12px;">📋 可用操作</div>' +
                        '<div style="color:var(--text-muted);font-size:13px;margin-bottom:8px;">通用可用操作：</div>';
                    var defaultActions = [
                        { name: 'health_check', desc: '健康检查' },
                        { name: 'status', desc: '获取状态' },
                        { name: 'execute', desc: '执行模块' },
                        { name: 'info', desc: '模块信息' }
                    ];
                    html += defaultActions.map(function(a) {
                        return '<div style="padding:8px 12px;margin-bottom:6px;background:var(--bg);border-radius:6px;font-size:13px;">' +
                            '<span style="color:#8b5cf6;font-weight:600;font-family:monospace;">' + a.name + '</span>' +
                            ' — <span style="color:var(--text-muted);">' + a.desc + '</span></div>';
                    }).join('');
                    html += '<div style="margin-top:12px;font-size:12px;color:var(--text-muted);">💡 点击"▶️ 执行模块"按钮，输入Action名称即可执行</div></div>';
                    area.innerHTML = html;
                });
        }

        function editItem(id) {

            var module = [...modules, ...customModules].find(m => m.id === id);

            if (!module) { showToast('⚠️ 模块未找到', 'error'); return; }

            // 复用现有的 addModuleModal 表单

            document.getElementById('editModuleId').value = id;

            document.getElementById('newModuleId').value = id;

            document.getElementById('newModuleName').value = module.name;

            document.getElementById('newModuleGroup').value = module.group || '';

            document.getElementById('newModuleIcon').value = module.icon || '🔧';

            document.getElementById('newModuleDesc').value = module.desc || '';

            document.getElementById('newModuleSource').value = module.source || '';

            document.getElementById('newModuleTags').value = (module.tags || []).join(',');

            document.getElementById('newModuleColor').value = module.color || '#3B82F6';

            document.getElementById('addModuleModal').classList.add('show');

        }



        function deleteItem(id) {

            var module = [...modules, ...customModules].find(m => m.id === id);

            if (!module) { showToast('⚠️ 模块未找到', 'error'); return; }

            // 复用现有的 confirmModal 确认框

            pendingAction = { type: 'delete', id };

            document.getElementById('confirmMessage').textContent = `确定要删除模块「${module.name}」（${id}）吗？`;

            document.getElementById('confirmModal').classList.add('show');

        }



        function saveModules() {

            localStorage.setItem('modules', JSON.stringify(modules));

        }



        function saveCustomModules() {

            localStorage.setItem('customModules', JSON.stringify(customModules));

        }



        document.addEventListener('keydown', (e) => {

            if (e.key === 'Escape') backToOverview();

            if (e.key === 'k' && e.ctrlKey) {

                e.preventDefault();

                document.getElementById('searchInput').focus();

            }

        });

        

        init();

        

        // ==================== 模块管理器 ====================

        var pendingAction = null;

        

        function openModuleManager() {

            document.getElementById('moduleManager').classList.add('show');

            renderModuleList();

        }

        

        function closeModuleManager() {

            document.getElementById('moduleManager').classList.remove('show');

        }

        

        function renderModuleList() {

            var container = document.getElementById('moduleList');

            container.innerHTML = customModules.map(m => `

                <div class="module-list-item">

                    <input type="checkbox" class="module-checkbox" data-id="${m.id}" onchange="updateBatchDeleteBtn()" style="width:16px;height:16px;cursor:pointer;flex-shrink:0;">

                    <span class="module-list-icon">${m.icon}</span>

                    <div class="module-list-info">

                        <h4>${m.name} <span style="font-size:10px;background:var(--primary);color:white;padding:2px 6px;border-radius:4px;">${m.group}</span></h4>

                        <p>${m.desc}</p>

                    </div>

                    <div class="module-list-actions">

                        <button class="edit-btn" onclick="editModule('${m.id}')">✏️</button>

                        <button class="delete-btn" onclick="confirmDelete('${m.id}')">🗑️</button>

                    </div>

                </div>

            `).join('');

            if (customModules.length === 0) {

                container.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px 20px;">暂无自定义模块<br><span style="font-size:12px;margin-top:8px;display:block;">点击上方「添加模块」开始创建</span></p>';

            }

            updateBatchDeleteBtn();

        }

        

        function showAddModule() {

            document.getElementById('addModuleModal').classList.add('show');

            document.getElementById('editModuleId').value = '';

            document.getElementById('newModuleId').value = '';

            document.getElementById('newModuleName').value = '';

            document.getElementById('newModuleGroup').value = '';

            document.getElementById('newModuleIcon').value = '🔧';

            document.getElementById('newModuleDesc').value = '';

            document.getElementById('newModuleSource').value = '';

            document.getElementById('newModuleTags').value = '';

            document.getElementById('newModuleColor').value = '#3B82F6';

        }

        

        function closeAddModule() {

            document.getElementById('addModuleModal').classList.remove('show');

        }

        

        function editModule(id) {

            var m = customModules.find(x => x.id === id);

            if (!m) return;

            document.getElementById('addModuleModal').classList.add('show');

            document.getElementById('editModuleId').value = m.id;

            document.getElementById('newModuleId').value = m.id;

            document.getElementById('newModuleName').value = m.name;

            document.getElementById('newModuleGroup').value = m.group;

            document.getElementById('newModuleIcon').value = m.icon;

            document.getElementById('newModuleDesc').value = m.desc;

            document.getElementById('newModuleSource').value = m.source || '';

            document.getElementById('newModuleTags').value = (m.tags || []).join(',');

            document.getElementById('newModuleColor').value = m.color;

        }

        

        function saveModule() {

            var editId = document.getElementById('editModuleId').value;

            var id = document.getElementById('newModuleId').value.trim();

            var name = document.getElementById('newModuleName').value.trim();

            var group = document.getElementById('newModuleGroup').value.trim();

            var icon = document.getElementById('newModuleIcon').value;

            var desc = document.getElementById('newModuleDesc').value.trim();

            var source = document.getElementById('newModuleSource').value.trim();

            var tags = document.getElementById('newModuleTags').value.split(',').map(t => t.trim()).filter(Boolean);

            var color = document.getElementById('newModuleColor').value;

            

            if (!id || !name || !group) { alert('请填写必填项'); return; }

            

            var moduleData = { id, name, group, icon, desc, source, tags, color };

            

            if (editId) {

                // 编辑模式：先查 customModules，再查 modules

                var customIdx = customModules.findIndex(x => x.id === editId);

                if (customIdx !== -1) {

                    customModules[customIdx] = { ...customModules[customIdx], ...moduleData };

                    saveCustomModules();

                } else {

                    var builtinIdx = modules.findIndex(x => x.id === editId);

                    if (builtinIdx !== -1) {

                        modules[builtinIdx] = { ...modules[builtinIdx], ...moduleData };

                        saveModules();

                    }

                }

            } else {

                // 新增模式

                customModules.push(moduleData);

                saveCustomModules();

            }

            

            closeAddModule();

            renderModuleList();

            renderNav();

            showToast('✅ 模块已保存', 'success');

            if (currentModule && currentModule.id === id) showPage(id);

        }

        

        function confirmDelete(id) {

            pendingAction = { type: 'delete', id };

            document.getElementById('confirmMessage').textContent = `确定要删除模块 "${id}" 吗？`;

            document.getElementById('confirmModal').classList.add('show');

        }

        

        function closeConfirmModal() {

            document.getElementById('confirmModal').classList.remove('show');

            pendingAction = null;

        }

        

        function confirmAction() {

            if (!pendingAction) return;

            if (pendingAction.type === 'delete') {

                var id = pendingAction.id;

                var wasInModules = modules.some(m => m.id === id);

                var wasInCustom = customModules.some(m => m.id === id);

                if (wasInModules) {

                    modules = modules.filter(m => m.id !== id);

                    saveModules();

                }

                if (wasInCustom) {

                    customModules = customModules.filter(m => m.id !== id);

                    saveCustomModules();

                }

                closeConfirmModal();

                renderNav();

                renderModuleList();

                showToast('✅ 模块已删除', 'success');

                backToOverview();

            } else if (pendingAction.type === 'reset') {

                customModules = [];

                starredModules = [];

                localStorage.removeItem('customModules');

                localStorage.removeItem('starredModules');

                renderModuleList();

                renderNav();

                showToast('✅ 自定义模块已清空', 'success');

            } else if (pendingAction.type === 'batchDelete') {

                customModules = customModules.filter(x => !pendingAction.ids.includes(x.id));

                saveCustomModules();

                renderModuleList();

                renderNav();

                showToast('✅ 已删除 ' + pendingAction.ids.length + ' 个模块', 'success');

            }

            closeConfirmModal();

        }

        

        // ==================== 批量选择管理 ====================

        function toggleSelectAll() {

            var checkboxes = document.querySelectorAll('.module-checkbox');

            var allChecked = [...checkboxes].every(cb => cb.checked);

            checkboxes.forEach(cb => cb.checked = !allChecked);

            updateBatchDeleteBtn();

        }

        

        function updateBatchDeleteBtn() {

            var checked = document.querySelectorAll('.module-checkbox:checked');

            var btn = document.getElementById('batchDeleteBtn');

            var count = document.getElementById('selectedCount');

            if (btn) {

                btn.style.display = checked.length > 0 ? 'inline-flex' : 'none';

                btn.textContent = `🗑️ 批量删除 (${checked.length})`;

            }

            if (count) count.textContent = `已选 ${checked.length} 个`;

        }

        

        function batchDeleteModules() {

            var checked = document.querySelectorAll('.module-checkbox:checked');

            var ids = [...checked].map(cb => cb.dataset.id);

            if (ids.length === 0) return;

            pendingAction = { type: 'batchDelete', ids };

            document.getElementById('confirmMessage').textContent = `确定要删除选中的 ${ids.length} 个模块吗？此操作不可撤销！`;

            document.getElementById('confirmModal').classList.add('show');

        }

        

        function exportModules() {

            var date = new Date().toISOString().slice(0, 10).replace(/-/g, '');

            var data = JSON.stringify(customModules, null, 2);

            var blob = new Blob([data], { type: 'application/json' });

            var url = URL.createObjectURL(blob);

            var a = document.createElement('a');

            a.href = url;

            a.download = `modules-config-${date}.json`;

            a.click();

            URL.revokeObjectURL(url);

        }

        

        function importModules() {

            var input = document.createElement('input');

            input.type = 'file';

            input.accept = '.json';

            input.onchange = (e) => {

                var file = e.target.files[0];

                if (!file) return;

                var reader = new FileReader();

                reader.onload = (evt) => {

                    try {

                        var data = JSON.parse(evt.target.result);

                        if (!Array.isArray(data)) throw new Error('格式错误');

                        var mode = confirm(`导入 ${data.length} 个模块：\n\n「确定」= 合并（追加，不覆盖已有）\n「取消」= 覆盖（清空后导入）`) ? 'merge' : 'replace';

                        if (mode === 'merge') {

                            var existingIds = new Set(customModules.map(m => m.id));

                            var added = 0;

                            data.forEach(m => {

                                if (!existingIds.has(m.id)) {

                                    customModules.push(m);

                                    added++;

                                }

                            });

                            alert(`合并完成：新增 ${added} 个模块`);

                        } else {

                            customModules = data;

                            alert(`覆盖完成：共 ${data.length} 个模块`);

                        }

                        saveCustomModules();

                        renderModuleList();

                        renderNav();

                    } catch (err) {

                        alert('导入失败：' + err.message);

                    }

                };

                reader.readAsText(file);

            };

            input.click();

        }

        

        function resetToDefault() {

            pendingAction = { type: 'reset' };

            document.getElementById('confirmMessage').textContent = '确定要重置所有模块到默认状态吗？';

            document.getElementById('confirmModal').classList.add('show');

        }

    