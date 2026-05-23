# AUTO-EVO-AI V0.1 产品使用手册

> **一句话：配好 API Key，就能拥有上市公司级 AI 自动化生产力。**

---

## 📖 目录

1. [这是什么](#1-这是什么)
2. [3 分钟快速上手](#2-3-分钟快速上手)
3. [日常使用](#3-日常使用)
4. [一句话干活（自然语言）](#4-一句话干活自然语言)
5. [常见问题](#5-常见问题)
6. [技术规格](#6-技术规格)

---

## 1. 这是什么

AUTO-EVO-AI 是一个**一个人就能用的上市公司级 AI 自动化平台**。

### 它能自动做的事

```
⏰ 每天 9:00 → 自动扫 GitHub Trending → 钉钉推送
🩺 每小时 → 系统健康巡检 → 异常自动告警
🤖 每 30 分钟 → 智能体决策 → 故障自愈
💬 随时 → 说一句话 → 系统自动执行
```

### 一个人 = 一个团队

```
你                 系统自动完成
─────────────────────────────────────
SRE/运维     →     健康巡检 + 故障自愈
AI 工程师    →     LLM 网关 + 6 家厂商
技术调研     →     GitHub 趋势扫描
DevOps      →     Docker + CI/CD
QA          →     自动化测试
```

---

## 2. 3 分钟快速上手

### 第一步：启动系统

**方式一：Docker（推荐）**

```bash
# 只需要一行命令
docker compose up -d
```

**方式二：一键启动（Windows）**

```
双击「一键启动.bat」
等待 30 秒，系统就绪
```

### 第二步：找到你的钥匙

系统启动后，打开 `D:\AUTO-EVO-AI-V0.1\.api_key` 文件：

```
# AUTO-EVO-AI V0.1 API Key

y8hFqH3tCAOgUQBMxnJyb63D6mOV6N4wTRFHdjhX2qo
```

**这串字符就是你的钥匙，所有操作都需要它。**

### 第三步：打开设置向导

浏览器打开：

```
http://localhost:8765/wizard
```

![](https://via.placeholder.com/800x450/1a1a2e/ffffff?text=Step+1:+Open+Wizard)

**三步完成：**

```
步骤 1: 填 API Key
        智谱/OpenAI/DeepSeek 任选一家
        从厂商官网获取 Key，粘贴进来

步骤 2: 填通知地址（可选）
        钉钉/飞书/Slack 任选一个
        把群机器人的 Webhook URL 粘贴进来

步骤 3: 点「发送测试通知」
        系统自动发一条消息到你的群
        收到就说明一切就绪
```

### 你现在已经拥有了

```
✅ 15 个自动调度任务每天运行
✅ AI 大脑（智谱 GLM-4-Flash）
✅ 健康监控 + 异常告警
✅ 535 个模块随时调用
✅ 8 种语言界面切换
```

---

## 3. 日常使用

### 打开 Dashboard

```
http://localhost:8765/dashboard
```

![](https://via.placeholder.com/800x450/0f172a/ffffff?text=Dashboard+Overview)

顶部工具栏：

```
🧠 主编排器   📊 运营中心   📦 模块管理
📖 文档       🌐 隧道      ◀ 收起侧边栏
🇺🇳 语言切换  🌓 主题切换
```

### 查看系统状态

```
http://localhost:8765/ops
```

这里可以看到：

```
🏠 总览 → 系统健康、模块数、调度状态
⚙️ 配置 → LLM 配置、通知设置
⏰ 任务 → 调度任务列表、执行记录
📢 通知 → 通道状态、测试发送
📋 日志 → 最近执行日志
```

### 切换语言

点击顶部栏的 **🇺🇳** 按钮，选择你需要的语言：

```
中文 · English · 日本語 · 한국어
Tiếng Việt · ภาษาไทย · Bahasa · Melayu
```

---

## 4. 一句话干活（自然语言）

系统支持**说话就能干活**。不需要写代码，不需要查文档。

### 直接说

```bash
# 查看 GitHub 趋势
curl -X POST http://localhost:8765/api/workflow/goal \
  -H "X-API-Key: 你的KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "查看GitHub趋势"}'

# 返回:
# {"intent": "trend", "template": "GitHub趋势监控", "status": "已执行"}
```

```bash
# 检查系统健康
curl -X POST http://localhost:8765/api/workflow/goal \
  -H "X-API-Key: 你的KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "检查系统健康"}'

# 返回:
# {"intent": "health", "template": "健康巡检", "status": "已执行"}
```

### 支持的指令

```
你说                   系统理解          自动执行
─────────────────────────────────────────────────
"查看趋势"              trend            GitHub 扫描 + 分析
"检查健康"              health           健康巡检 + 告警
"系统状态"              status           模块 + 调度 + 资源
"发送通知"              notify           通知通道推送
"配置 LLM"              llm_config       LLM 厂商配置
```

---

## 5. 常见问题

### Q: 启动后浏览器打开没反应？

```
确认系统已启动:
  http://localhost:8765/api/status
  应该返回: {"system": "AUTO-EVO-AI V0.1", "status": "running"}
```

### Q: API Key 在哪里？

```
文件位置: D:\AUTO-EVO-AI-V0.1\.api_key
每次重启系统会生成新的 Key，从文件里读取即可
```

### Q: 通知没收到？

```
1. 确认 Webhook URL 正确
2. 用 curl 测试:
   curl -X POST http://localhost:8765/api/notify/test \
     -H "X-API-Key: 你的KEY" \
     -d '{"channel":"dingtalk","webhook_url":"你的URL","content":"测试"}'
```

### Q: 系统卡住了怎么办？

```
1. 重启服务: 重新双击「一键启动.bat」
2. 检查日志: http://localhost:8765/ops → 日志 Tab
3. 紧急恢复: Taskkill /F /IM python.exe → 重新启动
```

---

## 6. 技术规格

```
系统版本:   AUTO-EVO-AI V0.1
模块数量:   535 个（全部 A 级）
调度任务:   15 个（自启）
API 端点:   50+
LLM 厂商:   6 家（智谱/OpenAI/DeepSeek/千问/Claude/Gemini）
通知通道:   13 个
支持语言:   8 种
容器部署:   Docker + docker-compose
CI/CD:     GitHub Actions
安全:      API Key 强制 + 限流 + 审计
文档:      API/模块/架构三件套
```

---

> **有任何问题，打开浏览器访问 `http://localhost:8765/wizard`，跟着向导走就行。**
