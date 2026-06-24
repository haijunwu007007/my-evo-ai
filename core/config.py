"""系统配置 — 集中管理硬编码值"""
import os

# 路径配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in dir() else r'D:\AUTO-EVO-AI-V0.1'
MODULES_DIR = os.path.join(PROJECT_ROOT, 'modules')
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
API_DIR = os.path.join(PROJECT_ROOT, 'api', 'routes')

# 服务配置
API_HOST = os.environ.get('EVO_HOST', '0.0.0.0')
API_PORT = int(os.environ.get('EVO_PORT', '8765'))
DB_PATH = os.environ.get('EVO_DB', os.path.join(PROJECT_ROOT, 'evo.db'))

# GitHub 镜像（443不通时降级）
GITHUB_MIRRORS = [
    None,
    "https://ghproxy.com/",
    "https://hub.fastgit.xyz/",
    "https://github.moeyy.xyz/",
]

# 工作流默认
DEFAULT_WORKFLOWS = [
    {"id":"workflow-doc-auto","name":"文档自动化处理","trigger":"doc_auto"},
    {"id":"workflow-code-deploy","name":"代码审查→部署","trigger":"code_deploy"},
    {"id":"workflow-data-report","name":"数据分析→图表→报告","trigger":"data_report"},
    {"id":"workflow-stock-auto","name":"股票自动分析","trigger":"stock_auto"},
    {"id":"workflow-web-auto","name":"网页自动操作","trigger":"web_auto"},
    {"id":"workflow-meeting-auto","name":"会议→记录→总结","trigger":"meeting_auto"},
    {"id":"workflow-home-auto","name":"智能家居自动化","trigger":"home_auto"},
    {"id":"workflow-i18n-auto","name":"文档国际化","trigger":"i18n_auto"},
]

# n8n
N8N_URL = os.environ.get('N8N_URL', 'http://localhost:5678')
N8N_API_KEY = os.environ.get('N8N_API_KEY', '')

# 认证
MCP_AUTH_ENABLED = os.environ.get('MCP_AUTH', '1') == '1'
MCP_AUTH_TOKEN = os.environ.get('MCP_TOKEN', 'evo-mcp-token-2026')
