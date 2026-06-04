# AUTO-EVO-AI — 开源全栈 AI 自动化编排系统

## 一句话

> 一个自托管的 AI 工作站：457 模块 / 156 技能 / 101 集成 / MCP Gateway / 自主 Agent / RAG 知识库 / 桌面自动化 / 15 页管理后台。跑在你的 PC 或云服务器上，手机浏览器也能用。

## 它能做什么

| 功能 | 说明 |
|------|------|
| 🧠 **AI 对话** | GLM-4/Ollama/OpenAI，有 Key 走 AI，无 Key 降级规则 |
| 📝 **文档生成** | 说"帮我写合同"直接出 Word，做 PPT/Excel 也一样 |
| 🔥 **GitHub 热门** | 实时 TOP 10，中文返回 |
| 🔍 **网页搜索** | DuckDuckGo + crawl4ai AI 爬虫 |
| 🧮 **数学计算** | 本地引擎，500+450+520=1470 |
| 🌐 **翻译九语** | 中/英/日/韩/法/西/葡/俄/阿 |
| 🧠 **持久记忆** | "记住xxx"→SQLite，"我记得"→查询 |
| 📋 **待办看板** | "记下明天开会"→CRUD API |
| 🖥️ **桌面控制** | 截图/打开计算器/记事本/浏览器 |
| 🐳 **Docker 部署** | Portainer/Gitea/Metabase 一行启动 |
| 🔌 **101 集成** | GitHub/Slack/Stripe/MySQL/OpenAI 等 |
| 🎨 **MCPize** | 任意网站/API/CLI/Python → MCP 工具 |
| 🤖 **A2A Agent** | 6 人 AI 团队：planner/coder/reviewer 等 |
| 🔄 **REST→MCP** | 给 OpenAPI URL 自动转 MCP 工具 |
| 📱 **PWA 离线** | 手机浏览器访问，Service Worker 缓存 |
| 🔑 **公开 API** | 嵌入别人网站一行代码就有 AI 客服 |

## 技术栈

- **后端**: Python 3.13+ / FastAPI / 14 个路由文件
- **前端**: 纯 HTML/CSS/JS / PWA / 15 页管理后台
- **存储**: SQLite / 文件系统
- **AI**: GLM-4 / OpenAI / Ollama / DuckDuckGo
- **协议**: MCP (JSON-RPC) / A2A / REST

## 快速开始

```bash
git clone https://github.com/haijunwu007007/my-evo-ai.git
cd my-evo-ai
pip install -r requirements.txt
python -m uvicorn api_server:app --host 0.0.0.0 --port 8765
# 浏览器打开 http://localhost:8765
```

## 截图

（此处放截图）

## 链接

- GitHub: https://github.com/haijunwu007007/my-evo-ai
- 在线体验: http://你的服务器:8765
- 作者: @haijunwu007007

---

欢迎 Star / Issue / PR。觉得有用请分享。
