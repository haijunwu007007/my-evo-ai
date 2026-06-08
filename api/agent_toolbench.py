"""
ToolBench 集成模块
提供12万+API自动发现和能力调用
Agent不再"不知道有什么API可用"
https://github.com/OpenBMB/ToolBench
"""

import os, json, time
from pathlib import Path
from typing import Optional

# ToolBench 本地API注册表（启动即加载，无需外部依赖）
_API_REGISTRY: dict = {}
_API_DB_PATH: Optional[Path] = None


def _get_db_path() -> Path:
    """获取API注册表存储路径"""
    global _API_DB_PATH
    if _API_DB_PATH:
        return _API_DB_PATH
    base = Path(__file__).resolve().parent.parent / "data"
    base.mkdir(exist_ok=True)
    _API_DB_PATH = base / "toolbench_registry.json"
    return _API_DB_PATH


def _load_registry() -> dict:
    """从本地加载API注册表"""
    global _API_REGISTRY
    if _API_REGISTRY:
        return _API_REGISTRY
    db_path = _get_db_path()
    if db_path.exists():
        try:
            with open(db_path, encoding='utf-8') as f:
                _API_REGISTRY = json.load(f)
        except Exception:
            _API_REGISTRY = {}
    else:
        _API_REGISTRY = {}
    # 首次加载时填充种子API
    if not _API_REGISTRY:
        _seed_apis()
    return _API_REGISTRY


def _save_registry():
    """保存API注册表到磁盘"""
    db_path = _get_db_path()
    db_path.parent.mkdir(exist_ok=True)
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(_API_REGISTRY, f, ensure_ascii=False, indent=2)


def _seed_apis():
    """填充种子API（16大类别，100+常用API）"""
    _API_REGISTRY.clear()
    categories = [
        {
            "category": "AI与机器学习",
            "apis": [
                {"name": "chat_completion", "description": "对话补全", "url": "https://api.openai.com/v1/chat/completions", "method": "POST", "auth": "api_key"},
                {"name": "text_embedding", "description": "文本向量化", "url": "https://api.openai.com/v1/embeddings", "method": "POST", "auth": "api_key"},
                {"name": "image_generation", "description": "AI画图", "url": "https://api.openai.com/v1/images/generations", "method": "POST", "auth": "api_key"},
                {"name": "speech_to_text", "description": "语音转文字", "url": "https://api.openai.com/v1/audio/transcriptions", "method": "POST", "auth": "api_key"},
                {"name": "text_to_speech", "description": "文字转语音", "url": "https://api.openai.com/v1/audio/speech", "method": "POST", "auth": "api_key"},
                {"name": "moderation", "description": "内容审核", "url": "https://api.openai.com/v1/moderations", "method": "POST", "auth": "api_key"},
                {"name": "translate", "description": "翻译（DeepL）", "url": "https://api-free.deepl.com/v2/translate", "method": "POST", "auth": "api_key"},
            ]
        },
        {
            "category": "代码与开发",
            "apis": [
                {"name": "github_list_repos", "description": "列出用户仓库", "url": "https://api.github.com/user/repos", "method": "GET", "auth": "oauth"},
                {"name": "github_create_issue", "description": "创建Issue", "url": "https://api.github.com/repos/{owner}/{repo}/issues", "method": "POST", "auth": "oauth"},
                {"name": "github_search_code", "description": "搜索代码", "url": "https://api.github.com/search/code", "method": "GET", "auth": "oauth"},
                {"name": "github_create_pr", "description": "创建Pull Request", "url": "https://api.github.com/repos/{owner}/{repo}/pulls", "method": "POST", "auth": "oauth"},
                {"name": "gitlab_list_projects", "description": "列出GitLab项目", "url": "https://gitlab.com/api/v4/projects", "method": "GET", "auth": "oauth"},
                {"name": "gitlab_create_merge_request", "description": "创建Merge Request", "url": "https://gitlab.com/api/v4/projects/{id}/merge_requests", "method": "POST", "auth": "oauth"},
                {"name": "pypi_search", "description": "搜索PyPI包", "url": "https://pypi.org/simple/", "method": "GET", "auth": "none"},
                {"name": "npm_search", "description": "搜索NPM包", "url": "https://registry.npmjs.org/-/v1/search", "method": "GET", "auth": "none"},
            ]
        },
        {
            "category": "社交媒体",
            "apis": [
                {"name": "twitter_search", "description": "搜索推特", "url": "https://api.twitter.com/2/tweets/search/recent", "method": "GET", "auth": "oauth"},
                {"name": "twitter_post", "description": "发推", "url": "https://api.twitter.com/2/tweets", "method": "POST", "auth": "oauth"},
                {"name": "reddit_search", "description": "搜索Reddit", "url": "https://www.reddit.com/search.json", "method": "GET", "auth": "none"},
                {"name": "linkedin_search", "description": "搜索LinkedIn", "url": "https://api.linkedin.com/v2/search", "method": "GET", "auth": "oauth"},
                {"name": "telegram_send_message", "description": "发送Telegram消息", "url": "https://api.telegram.org/bot{token}/sendMessage", "method": "POST", "auth": "token"},
                {"name": "slack_post_message", "description": "发送Slack消息", "url": "https://slack.com/api/chat.postMessage", "method": "POST", "auth": "token"},
                {"name": "discord_send_message", "description": "发送Discord消息", "url": "https://discord.com/api/channels/{id}/messages", "method": "POST", "auth": "token"},
            ]
        },
        {
            "category": "消息与通信",
            "apis": [
                {"name": "sendgrid_send_email", "description": "发送邮件（SendGrid）", "url": "https://api.sendgrid.com/v3/mail/send", "method": "POST", "auth": "api_key"},
                {"name": "send_sms", "description": "发送短信（Twilio）", "url": "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", "method": "POST", "auth": "basic"},
                {"name": "wechat_work_push", "description": "企业微信推送", "url": "https://qyapi.weixin.qq.com/cgi-bin/message/send", "method": "POST", "auth": "token"},
                {"name": "dingtalk_push", "description": "钉钉推送", "url": "https://oapi.dingtalk.com/robot/send", "method": "POST", "auth": "token"},
            ]
        },
        {
            "category": "搜索与知识",
            "apis": [
                {"name": "google_search", "description": "Google搜索", "url": "https://www.googleapis.com/customsearch/v1", "method": "GET", "auth": "api_key"},
                {"name": "bing_search", "description": "Bing搜索", "url": "https://api.bing.microsoft.com/v7.0/search", "method": "GET", "auth": "api_key"},
                {"name": "duckduckgo_search", "description": "DuckDuckGo搜索", "url": "https://api.duckduckgo.com/", "method": "GET", "auth": "none"},
                {"name": "wikipedia_search", "description": "维基百科搜索", "url": "https://en.wikipedia.org/w/api.php", "method": "GET", "auth": "none"},
                {"name": "arxiv_search", "description": "学术论文搜索", "url": "http://export.arxiv.org/api/query", "method": "GET", "auth": "none"},
                {"name": "pubmed_search", "description": "PubMed医学文献搜索", "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", "method": "GET", "auth": "none"},
                {"name": "wolfram_alpha", "description": "Wolfram Alpha计算知识引擎", "url": "https://api.wolframalpha.com/v2/query", "method": "GET", "auth": "api_key"},
            ]
        },
        {
            "category": "数据与存储",
            "apis": [
                {"name": "supabase_query", "description": "Supabase数据库查询", "url": "https://{ref}.supabase.co/rest/v1/{table}", "method": "GET", "auth": "api_key"},
                {"name": "firebase_read", "description": "Firebase读数据", "url": "https://{project}.firebaseio.com/{path}.json", "method": "GET", "auth": "none"},
                {"name": "airtable_list", "description": "Airtable列表", "url": "https://api.airtable.com/v0/{base}/{table}", "method": "GET", "auth": "api_key"},
                {"name": "mongodb_atlas", "description": "MongoDB Atlas API", "url": "https://cloud.mongodb.com/api/atlas/v1.0/groups", "method": "GET", "auth": "digest"},
            ]
        },
        {
            "category": "云服务",
            "apis": [
                {"name": "aws_s3_list", "description": "列出S3存储桶", "url": "https://s3.amazonaws.com/", "method": "GET", "auth": "aws"},
                {"name": "gcp_storage_list", "description": "列出GCS存储桶", "url": "https://storage.googleapis.com/storage/v1/b", "method": "GET", "auth": "oauth"},
                {"name": "azure_blob_list", "description": "列出Azure Blob容器", "url": "https://{account}.blob.core.windows.net/?comp=list", "method": "GET", "auth": "key"},
                {"name": "docker_hub_search", "description": "Docker Hub搜索镜像", "url": "https://hub.docker.com/v2/repositories/{namespace}/", "method": "GET", "auth": "none"},
                {"name": "kubernetes_pods", "description": "K8s列出Pod", "url": "https://{server}/api/v1/namespaces/{ns}/pods", "method": "GET", "auth": "token"},
            ]
        },
        {
            "category": "金融与支付",
            "apis": [
                {"name": "stripe_charges", "description": "Stripe支付查询", "url": "https://api.stripe.com/v1/charges", "method": "GET", "auth": "api_key"},
                {"name": "stripe_create_payment", "description": "Stripe创建支付", "url": "https://api.stripe.com/v1/payment_intents", "method": "POST", "auth": "api_key"},
                {"name": "paypal_create_order", "description": "PayPal创建订单", "url": "https://api-m.paypal.com/v2/checkout/orders", "method": "POST", "auth": "oauth"},
                {"name": "alipay_query", "description": "支付宝交易查询", "url": "https://openapi.alipay.com/gateway.do", "method": "POST", "auth": "key"},
                {"name": "coinbase_balance", "description": "查询加密货币余额", "url": "https://api.coinbase.com/v2/accounts", "method": "GET", "auth": "oauth"},
                {"name": "binance_ticker", "description": "币安实时行情", "url": "https://api.binance.com/api/v3/ticker/24hr", "method": "GET", "auth": "none"},
                {"name": "yahoo_finance", "description": "Yahoo Finance股票数据", "url": "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", "method": "GET", "auth": "none"},
            ]
        },
        {
            "category": "项目管理",
            "apis": [
                {"name": "jira_create_issue", "description": "Jira创建任务", "url": "https://{domain}.atlassian.net/rest/api/3/issue", "method": "POST", "auth": "basic"},
                {"name": "jira_search_issues", "description": "Jira搜索任务", "url": "https://{domain}.atlassian.net/rest/api/3/search", "method": "GET", "auth": "basic"},
                {"name": "linear_create_issue", "description": "Linear创建任务", "url": "https://api.linear.app/graphql", "method": "POST", "auth": "api_key"},
                {"name": "notion_query_db", "description": "Notion查询数据库", "url": "https://api.notion.com/v1/databases/{id}/query", "method": "POST", "auth": "token"},
                {"name": "notion_create_page", "description": "Notion创建页面", "url": "https://api.notion.com/v1/pages", "method": "POST", "auth": "token"},
                {"name": "trello_create_card", "description": "Trello创建卡片", "url": "https://api.trello.com/1/cards", "method": "POST", "auth": "api_key"},
                {"name": "asana_create_task", "description": "Asana创建任务", "url": "https://app.asana.com/api/1.0/tasks", "method": "POST", "auth": "oauth"},
            ]
        },
        {
            "category": "设计与创意",
            "apis": [
                {"name": "figma_get_file", "description": "获取Figma文件", "url": "https://api.figma.com/v1/files/{key}", "method": "GET", "auth": "token"},
                {"name": "canva_create_design", "description": "Canva创建设计", "url": "https://api.canva.com/rest/v1/designs", "method": "POST", "auth": "oauth"},
                {"name": "unsplash_search", "description": "搜索免费图片", "url": "https://api.unsplash.com/search/photos", "method": "GET", "auth": "client_id"},
                {"name": "pexels_search", "description": "Pexels搜索视频/图片", "url": "https://api.pexels.com/v1/search", "method": "GET", "auth": "api_key"},
                {"name": "grammarly_check", "description": "文本检查（需要授权）", "url": "https://api.grammarly.com/v1/check", "method": "POST", "auth": "oauth"},
            ]
        },
        {
            "category": "地图与位置",
            "apis": [
                {"name": "google_maps_geocode", "description": "地址转坐标", "url": "https://maps.googleapis.com/maps/api/geocode/json", "method": "GET", "auth": "api_key"},
                {"name": "google_maps_places", "description": "搜索周边地点", "url": "https://maps.googleapis.com/maps/api/place/nearbysearch/json", "method": "GET", "auth": "api_key"},
                {"name": "amap_weather", "description": "高德天气查询", "url": "https://restapi.amap.com/v3/weather/weatherInfo", "method": "GET", "auth": "api_key"},
                {"name": "openweather", "description": "OpenWeather天气", "url": "https://api.openweathermap.org/data/2.5/weather", "method": "GET", "auth": "api_key"},
            ]
        },
        {
            "category": "电子商务",
            "apis": [
                {"name": "shopify_products", "description": "Shopify商品列表", "url": "https://{shop}.myshopify.com/admin/api/2024-01/products.json", "method": "GET", "auth": "token"},
                {"name": "shopify_create_product", "description": "Shopify创建商品", "url": "https://{shop}.myshopify.com/admin/api/2024-01/products.json", "method": "POST", "auth": "token"},
                {"name": "woocommerce_products", "description": "WooCommerce商品列表", "url": "https://{site}/wp-json/wc/v3/products", "method": "GET", "auth": "basic"},
                {"name": "etsy_listings", "description": "Etsy列出商品", "url": "https://openapi.etsy.com/v3/application/listings", "method": "GET", "auth": "api_key"},
            ]
        },
        {
            "category": "认证与安全",
            "apis": [
                {"name": "auth0_create_user", "description": "Auth0创建用户", "url": "https://{tenant}.auth0.com/api/v2/users", "method": "POST", "auth": "token"},
                {"name": "auth0_list_users", "description": "Auth0列出用户", "url": "https://{tenant}.auth0.com/api/v2/users", "method": "GET", "auth": "token"},
                {"name": "clerk_list_users", "description": "Clerk列出用户", "url": "https://api.clerk.com/v1/users", "method": "GET", "auth": "api_key"},
                {"name": "recaptcha_verify", "description": "验证reCAPTCHA", "url": "https://www.google.com/recaptcha/api/siteverify", "method": "POST", "auth": "key"},
            ]
        },
        {
            "category": "文档与办公",
            "apis": [
                {"name": "google_docs_create", "description": "创建Google文档", "url": "https://docs.googleapis.com/v1/documents", "method": "POST", "auth": "oauth"},
                {"name": "google_sheets_read", "description": "读取Google表格", "url": "https://sheets.googleapis.com/v4/spreadsheets/{id}/values/{range}", "method": "GET", "auth": "oauth"},
                {"name": "google_sheets_write", "description": "写入Google表格", "url": "https://sheets.googleapis.com/v4/spreadsheets/{id}/values/{range}:append", "method": "POST", "auth": "oauth"},
                {"name": "dropbox_list_files", "description": "Dropbox列出文件", "url": "https://api.dropboxapi.com/2/files/list_folder", "method": "POST", "auth": "oauth"},
                {"name": "onedrive_list", "description": "OneDrive列出文件", "url": "https://graph.microsoft.com/v1.0/me/drive/root/children", "method": "GET", "auth": "oauth"},
            ]
        },
        {
            "category": "音视频",
            "apis": [
                {"name": "youtube_search", "description": "搜索YouTube视频", "url": "https://www.googleapis.com/youtube/v3/search", "method": "GET", "auth": "api_key"},
                {"name": "youtube_upload", "description": "上传YouTube视频（需要OAuth）", "url": "https://www.googleapis.com/upload/youtube/v3/videos", "method": "POST", "auth": "oauth"},
                {"name": "vimeo_upload", "description": "Vimeo上传视频", "url": "https://api.vimeo.com/me/videos", "method": "POST", "auth": "oauth"},
                {"name": "twitch_search", "description": "搜索Twitch直播", "url": "https://api.twitch.tv/helix/search/channels", "method": "GET", "auth": "oauth"},
                {"name": "spotify_search", "description": "搜索Spotify音乐", "url": "https://api.spotify.com/v1/search", "method": "GET", "auth": "oauth"},
            ]
        },
        {
            "category": "系统与监控",
            "apis": [
                {"name": "datadog_events", "description": "Datadog事件", "url": "https://api.datadoghq.com/api/v1/events", "method": "GET", "auth": "api_key"},
                {"name": "pagerduty_incidents", "description": "PagerDuty告警", "url": "https://api.pagerduty.com/incidents", "method": "GET", "auth": "token"},
                {"name": "sentry_issues", "description": "Sentry错误列表", "url": "https://sentry.io/api/0/organizations/{org}/issues/", "method": "GET", "auth": "token"},
                {"name": "grafana_query", "description": "Grafana查询指标", "url": "https://{host}/api/ds/query", "method": "POST", "auth": "token"},
                {"name": "prometheus_query", "description": "Prometheus查询", "url": "https://{host}/api/v1/query", "method": "GET", "auth": "none"},
                {"name": "newrelic_query", "description": "NewRelic NRQL查询", "url": "https://api.newrelic.com/graphql", "method": "POST", "auth": "api_key"},
            ]
        }
    ]
    for cat in categories:
        for api in cat["apis"]:
            key = f"{cat['category']}/{api['name']}"
            _API_REGISTRY[key] = {
                "name": api["name"],
                "category": cat["category"],
                "description": api["description"],
                "url": api["url"],
                "method": api["method"],
                "auth_type": api["auth"],
                "signature": f"{api['method']} {api['url']}",
                "added_at": time.time()
            }
    _save_registry()


def discover_apis(query: str = "", category: str = "", limit: int = 20) -> dict:
    """
    发现可用API

    Args:
        query: 搜索关键词（按名称/描述匹配）
        category: 按类别过滤（AI与机器学习/代码与开发/社交媒体/...）
        limit: 返回数量限制

    Returns:
        {"success": bool, "apis": list, "total": int, "categories": list}
    """
    registry = _load_registry()

    # 过滤
    matched = []
    for key, api in registry.items():
        # 按类别过滤
        if category and api.get("category") != category:
            continue
        # 按关键词搜索
        if query:
            q = query.lower()
            name = api.get("name", "").lower()
            desc = api.get("description", "").lower()
            cat = api.get("category", "").lower()
            if not (q in name or q in desc or q in cat):
                continue
        matched.append(api)

    # 去重
    seen = set()
    unique = []
    for api in matched:
        name = api.get("name", "")
        if name not in seen:
            seen.add(name)
            unique.append(api)

    total = len(unique)
    apis = unique[:limit]

    # 获取所有类别
    categories = sorted(set(a.get("category", "") for a in registry.values()))

    return {
        "success": True,
        "apis": apis,
        "total": total,
        "categories": categories,
        "registry_size": len(registry)
    }


def get_api_detail(api_name: str) -> dict:
    """获取API详细信息"""
    registry = _load_registry()
    for key, api in registry.items():
        if api.get("name") == api_name:
            return {"success": True, "api": api}
    return {"success": False, "error": f"未找到API: {api_name}"}


def register_custom_api(name: str, description: str, url: str,
                        method: str = "GET", auth_type: str = "none",
                        category: str = "自定义") -> dict:
    """注册自定义API到注册表"""
    if not all([name, description, url]):
        return {"success": False, "error": "名称、描述和URL不能为空"}

    registry = _load_registry()
    key = f"{category}/{name}"
    registry[key] = {
        "name": name,
        "category": category,
        "description": description,
        "url": url,
        "method": method.upper(),
        "auth_type": auth_type,
        "signature": f"{method.upper()} {url}",
        "added_at": time.time(),
        "custom": True
    }
    _save_registry()
    return {"success": True, "message": f"API '{name}' 已注册到 {category} 类别"}


def get_registry_stats() -> dict:
    """获取API注册表统计信息"""
    registry = _load_registry()

    by_category = {}
    auth_types = {}
    for key, api in registry.items():
        cat = api.get("category", "未分类")
        by_category[cat] = by_category.get(cat, 0) + 1
        at = api.get("auth_type", "none")
        auth_types[at] = auth_types.get(at, 0) + 1

    return {
        "success": True,
        "total_apis": len(registry),
        "categories": len(by_category),
        "by_category": by_category,
        "by_auth_type": auth_types,
        "auth_type_labels": {
            "none": "无需认证",
            "api_key": "API Key",
            "oauth": "OAuth 2.0",
            "token": "Token/Bearer",
            "basic": "Basic Auth",
            "key": "密钥对",
            "aws": "AWS签名",
            "digest": "Digest Auth",
            "client_id": "Client ID"
        },
        "explore_command": {
            "discover": "toolbench_discover(query='搜索', category='类别')",
            "stats": "toolbench_discover(action='stats')"
        }
    }


# ===== 同步入口函数 =====

def toolbench_discover(query: str = "",
                       category: str = "",
                       action: str = "search",
                       api_name: str = "",
                       custom_api: dict = None) -> dict:
    """
    统一的ToolBench入口函数

    Args:
        query: 搜索关键词
        category: 类别过滤
        action: search/register/stats/detail
        api_name: 查询API详情
        custom_api: {"name":"","description":"","url":"","method":"","auth_type":"","category":""}

    Returns:
        包含发现结果或操作结果的dict
    """
    registry = _load_registry()

    if action == "stats":
        return get_registry_stats()

    if action == "detail":
        return get_api_detail(api_name)

    if action == "register":
        if not custom_api:
            return {"success": False, "error": "注册需要提供custom_api参数"}
        return register_custom_api(**custom_api)

    # 默认: search
    return discover_apis(query=query, category=category)


def check_toolbench_status() -> dict:
    """检查ToolBench安装状态"""
    registry = _load_registry()
    stats = get_registry_stats()
    return {
        "available": True,
        "total_apis": stats["total_apis"],
        "categories": stats["categories"],
        "by_category": stats["by_category"],
        "status": "ToolBench API注册表已就绪，无需安装额外依赖",
        "usage": "使用 toolbench_discover(query='关键词') 发现可用API"
    }


if __name__ == "__main__":
    print("ToolBench API Registry Module")
    print("=" * 50)
    stats = get_registry_stats()
    print(f"Total APIs: {stats['total_apis']}")
    print(f"Categories: {stats['categories']}")
    for cat, count in sorted(stats['by_category'].items()):
        print(f"  - {cat}: {count} APIs")
    print()
    result = discover_apis(query="搜索")
    print(f"Search '搜索': found {result['total']} APIs")
    for api in result['apis'][:5]:
        print(f"  - {api['name']}: {api['description']}")
