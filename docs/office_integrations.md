# AUTO-EVO-AI 办公软件对接

## 8 大办公套件 API

| 办公套件 | 地区 | 对接方式 | 配置入口 |
|---|---|---|---|
| **飞书** | 🇨🇳 国内 | 消息推送+机器人 | `POST /api/integration/feishu` |
| **钉钉** | 🇨🇳 国内 | 消息推送+机器人 | `POST /api/integration/dingtalk` |
| **企业微信** | 🇨🇳 国内 | 消息推送 | `POST /api/integration/wechat` |
| **WPS 365** | 🇨🇳 国内 | 文档协作 | `POST /api/integration/wps` |
| **Microsoft 365** | 🌍 国外 | Graph API | `POST /api/integration/microsoft` |
| **Google Workspace** | 🌍 国外 | Gmail+Calendar API | `POST /api/integration/google` |
| **Slack** | 🌍 国外 | 消息推送+机器人 | `POST /api/integration/slack` |
| **Notion** | 🌍 国外 | 数据库+页面API | `POST /api/integration/notion` |
| **飞书文档** | 🇨🇳 国内 | 文档读写 | `POST /api/integration/feishu-doc` |
| **语雀** | 🇨🇳 国内 | 知识库API | `POST /api/integration/yuque` |

## 配置方法

### 飞书
```bash
curl -X POST http://localhost:8765/api/integration/feishu \
  -H "Content-Type: application/json" \
  -d '{"webhook_url":"https://open.feishu.cn/open-apis/bot/v2/hook/xxx","app_id":"xxx","app_secret":"xxx"}'
```

### 钉钉
```bash
curl -X POST http://localhost:8765/api/integration/dingtalk \
  -H "Content-Type: application/json" \
  -d '{"webhook_url":"https://oapi.dingtalk.com/robot/send?access_token=xxx"}'
```

### Microsoft 365
```bash
curl -X POST http://localhost:8765/api/integration/microsoft \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"xxx","client_id":"xxx","client_secret":"xxx"}'
```

### Google Workspace
```bash
curl -X POST http://localhost:8765/api/integration/google \
  -H "Content-Type: application/json" \
  -d '{"api_key":"xxx","client_id":"xxx"}'
```

## 查看已配置的集成
```bash
curl http://localhost:8765/api/integration/list
```
