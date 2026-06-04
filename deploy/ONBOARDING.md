# 🚀 5 分钟上手 AUTO-EVO-AI

## 第 0 分钟 — 启动

```bash
git clone https://github.com/haijunwu007007/my-evo-ai
cd my-evo-ai
pip install -r requirements.lock
uvicorn api_server:app --host 0.0.0.0 --port 8765
```

浏览器打开 `http://localhost:8765`

## 第 1 分钟 — 探索聊天界面

输入 `admin` 点"进入系统"。试试：

```
📌 说"你会什么" → 看到 40+ 功能列表
📌 说"帮我写一份合同" → 自动生成 Word 文档
📌 说"GitHub今天热门项目" → 实时 TOP 10
📌 说"帮我画一只猫" → 生成图片
📌 说"记住我叫张三" → 持久记忆
📌 说"2+2=?" → 数学计算
```

## 第 2 分钟 — 切换语言

点右上角语言按钮：
- 🇨🇳 中文 / 🇬🇧 English / 🇯🇵 日本語
- 界面和回复同步切换

## 第 3 分钟 — 管理后台

点右上角 ⚙️ 管理 进入后台：
- 📊 仪表盘 — 系统状态一览
- 🔧 技能浏览器 — 156 个技能
- 🌐 集成网关 — 101 个连接器
- 🤖 A2A — 6 人 Agent 团队
- 🐳 Docker — 一键部署工具

## 第 4 分钟 — MCPize 万能集成

把任意东西变成 AI 工具：

```bash
# 把 Python 模块变成工具
curl -X POST http://localhost:8765/api/v1/mcpize/python \
  -H "Content-Type: application/json" \
  -d '{"module":"json","name":"json-lib"}'

# 把网站变成工具
curl -X POST http://localhost:8765/api/v1/mcpize/website \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com","name":"github"}'

# 把命令行变成工具
curl -X POST http://localhost:8765/api/v1/mcpize/cli \
  -H "Content-Type: application/json" \
  -d '{"command":"whoami","name":"whoami"}'
```

## 第 5 分钟 — 嵌入到你的网站

```html
<script src="http://你的域名:8765/api/v1/public/embed.js"></script>
```

直接有 AI 客服。

---

**整个流程不超过 5 分钟。** 如果卡住了，提 Issue。
