# AUTO-EVO-AI V0.1 用户手册

> **上市级 AI 自动化编排系统**
> 版本：V0.1 | 更新：2026-06-02

---

## 目录

1. [系统简介](#1-系统简介)
2. [快速开始](#2-快速开始)
3. [Dashboard 监控面板](#3-dashboard-监控面板)
4. [模块管理](#4-模块管理)
5. [外部工具](#5-外部工具)
6. [Agent-S 桌面自动化](#6-agent-s-桌面自动化)
7. [语音输入](#7-语音输入)
8. [自动化工作流](#8-自动化工作流)
9. [系统设置](#9-系统设置)
10. [移动端使用](#10-移动端使用)
11. [常见问题](#11-常见问题)

---

## 1. 系统简介

AUTO-EVO-AI 是一个全栈 AI 自动化编排平台。它把 456 个 AI 能力模块、57 个外部工具、4 个核心引擎整合到一个统一的 Web 界面中。

**核心能力：**
- 全模块调度编排（456 个模块）
- 57 个第三方工具统一入口
- Agent-S 桌面 GUI 自动化
- 语音全局输入
- 自定义自动化工作流
- 亮暗主题切换

---

## 2. 快速开始

### 2.1 启动系统

**Windows：**
```powershell
右键 start.ps1 → 以管理员身份运行
```
自动完成：开防火墙 + 启动服务 + 显示访问地址

**手动启动：**
```powershell
cd D:\AUTO-EVO-AI-V0.1
python -m uvicorn api_server:app --host 0.0.0.0 --port 8765
```

### 2.2 访问系统

| 环境 | 地址 |
|------|------|
| 本机 | `http://localhost:8765/app/login` |
| 手机（同 WiFi） | `http://192.168.x.x:8765/app/login` |
| 外网 | 装 Tailscale 或部署到云服务器 |

### 2.3 首次设置

首次访问自动进入**设置向导**（3 步）：

1. **创建管理员账号** — 输入用户名（如 `admin`）
2. **配置 OpenAI API Key**（可选） — 用于 Agent-S 和 AI 任务
3. **完成** — 自动跳转 Dashboard

> 跳过设置向导后，每次打开登录页输入 `admin`（密码留空）即可登录。

---

## 3. Dashboard 监控面板

登录后进入 Dashboard，分 3 个区域：

### 3.1 顶部状态栏

| 指标 | 说明 |
|------|------|
| 🧠 系统状态 | 运行中/告警/离线 |
| 📊 模块统计 | 已加载 / 总数 / 桩模块数 |
| 📦 引擎状态 | 调度器 / 事件引擎 / 管线引擎 |
| ⏱ 运行时长 | 服务已运行时间 |
| 🔄 刷新按钮 | 手动刷新所有数据 |

### 3.2 核心指标（4 大块）

- **系统资源** — CPU / 内存实时使用率
- **请求趋势** — 30 分钟 API 请求量折线图
- **模块健康** — 已加载 vs 总模块环形图
- **活跃任务** — 当前正在执行的任务数

### 3.3 协调中心

输入任务描述 → 点"执行" → 系统自动调度 AI 处理：
```
# 示例
扫描 GitHub 热门 Python 项目
分析系统日志中的错误模式
生成今日系统健康报告
```

---

## 4. 模块管理

### 4.1 模块树

侧边栏 → **模块管理** → 左侧导航树展示 456 个模块，按类别分组：

- 🧠 系统大脑
- 🏛️ BILLION GROUP OS
- 🔐 安全 & 自愈
- 🤖 编程助手
- 📈 金融数据 API
- 🔧 运维保障
- ...（共 30+ 类别）

### 4.2 模块详情

点击任意模块 → 查看：

| 信息 | 说明 |
|------|------|
| 模块名称 | 中文 + 英文标识 |
| 版本 | V0.1 |
| 状态 | 已加载 / 未加载 |
| 健康检查 | 最近一次心跳时间 |
| 等级 | A/B/C 三级评估 |

### 4.3 搜索模块

顶部搜索框 → 输入关键词快速定位（支持模糊搜索）：
```
# 示例
股票
通知
安全
```

---

## 5. 外部工具

### 5.1 工具列表（57 个）

| 类别 | 工具 |
|------|------|
| 🤖 AI | Dify / Flowise / n8n / One-API / LiteLLM / Langfuse |
| 💻 开发 | Gitea / Code-Server |
| ☁️ 文件 | Nextcloud / MinIO / Stirling-PDF |
| 📊 数据 | Metabase / Meilisearch / NocoDB / Superset / Qdrant |
| 🔐 安全 | Vaultwarden / Portainer |
| 📈 监控 | Grafana / Uptime-Kuma / Prometheus |
| 🏢 企业 | Twenty CRM / Invoice Ninja / Chatwoot / osTicket |
| 🎬 媒体 | Jellyfin / Immich / Excalidraw / Calibre-Web |
| 👥 协作 | Docmost / Mattermost / Focalboard / Outline |
| 🏥 行业 | Medusa / OpenEMR |
| 💻 IT | Snipe-IT / IT-Tools / Miniflux |
| 📄 文档 | Paperless-ngx / Documenso |
| 📚 其他 | ERPNext / Frappe HR / Open edX / Home Assistant / Hoppscotch / Changedetection |

### 5.2 使用方式

1. 侧边栏 → **外部工具**
2. 点击工具卡片 → **打开面板**
3. 浏览器新标签页打开对应工具地址

> 工具需要先启动 Docker 容器才能访问。首次启动：
> ```bash
> docker compose -f docker-compose.tools.yml up -d
> ```

---

## 6. Agent-S 桌面自动化

### 6.1 前提

- 系统已安装 `gui-agents` SDK（V0.1 已预装）
- 需要配置 OpenAI API Key（在"API 配置"页面设置）

### 6.2 使用步骤

1. 侧边栏 → **Agent-S 桌面自动化**
2. 输入指令：
   ```
   打开记事本并输入 Hello World
   帮我截取当前屏幕
   获取鼠标位置
   ```
3. 选择模型（GPT-4o / Claude-3.5 等）
4. 点 **执行**

### 6.3 其他功能

- **桌面快照** — 截取当前屏幕
- **鼠标位置** — 获取鼠标坐标
- **环境检测** — 检查 SDK 和依赖完整性
- **执行历史** — 查看历史执行记录

---

## 7. 语音输入

### 7.1 全局语音

任何页面右下角的 **🎤 按钮**：

| 操作 | 说明 |
|------|------|
| 点 🎤 | 开始录音（浏览器请求麦克风权限） |
| 说话 | 自动中文语音识别 |
| 自动停止 | 说完自动停止，文字填入当前输入框 |
| 点 🔴 | 手动停止录音 |

### 7.2 支持页面

- Dashboard 协调中心输入框
- 模块管理搜索框
- 任何页面的输入框

> 需要 Chrome / Edge / Safari 浏览器。微信内置浏览器不支持。

---

## 8. 自动化工作流

### 8.1 内置模板

系统内置 3 个自动化工作流，可通过 API 触发：

| 工作流 | 流程 | 用途 |
|--------|------|------|
| 每日代码审查 | Gitea Issue → LLM 分析 → 报告 | 自动审查代码问题 |
| 系统健康日报 | 采集状态 → 生成报告 → 推送 | 每日系统巡检 |
| GitHub 趋势监控 | 抓趋势 → 筛选 → 提醒 | 跟踪热门项目 |

### 8.2 触发方式

```bash
# 执行工作流
curl -X POST http://localhost:8765/api/v1/workflow/run/system_health_report

# 查看执行历史
curl http://localhost:8765/api/v1/workflows
```

---

## 9. 系统设置

| 页面 | 功能 |
|------|------|
| API 配置 | 设置 OpenAI / 其他 LLM API Key |
| 调度器 | 查看/管理定时任务 |
| 事件引擎 | 查看系统事件流水 |
| 任务队列 | 查看排队中的任务 |
| 通知监控 | 配置钉钉/飞书/邮件通知 |
| 安全中心 | JWT / 权限配置 |
| SSO 管理 | 单点登录配置 |
| 系统设置 | 主题 / 语言 / 时区 |

### 9.1 主题切换

右上角 🌓 图标 → 一键切换亮色/暗色主题。

---

## 10. 移动端使用

### 10.1 手机浏览器访问

确保手机和电脑连同一个 WiFi：

```
http://电脑IP:8765/app/login
```

> 电脑 IP 查看方法：`ipconfig` → `IPv4 地址`

### 10.2 语音输入

手机浏览器（Chrome/Safari）支持音频输入：
- 点击输入框 → 弹出系统键盘 → 键盘上的 🎤 按钮
- 或使用系统的 🎤 全局语音按钮

### 10.3 外网远程访问

**方案一：Tailscale（推荐，免费）**

1. 电脑安装 [Tailscale](https://tailscale.com/download)
2. 手机安装 Tailscale
3. 登录同一账号
4. 手机浏览器访问：`http://100.x.x.x:8765/app/login`

**方案二：云服务器（约 30 元/月）**

买腾讯云/阿里云 2核2G → 联系我部署 → 手机直接访问服务器 IP。

---

## 11. 常见问题

### Q: 服务突然连不上了？
```
检查服务是否在运行：netstat -ano | findstr 8765
重新启动：运行 start.ps1
```

### Q: 登录密码是什么？
首次使用进入设置向导创建账号。如果直接登录，用户名 `admin`，密码留空。

### Q: 手机打不开页面？
- 检查手机和电脑是否同一 WiFi
- 检查防火墙是否开放 8765 端口（运行 start.ps1 自动配置）
- 尝试电脑 IP 而非 localhost

### Q: Agent-S 显示"SDK 未安装"？
服务需要运行在 Python 3.13+。确认启动命令使用的是正确 Python 版本：
```
C:\Users\吴海军\.workbuddy\binaries\python\versions\3.13.12\python.exe
```

### Q: 外部工具打不开？
工具需要先启动 Docker 容器：
```bash
docker compose -f docker-compose.tools.yml up -d 工具名
```

### Q: 如何备份系统？
配置文件和数据在以下目录：
```
D:\AUTO-EVO-AI-V0.1\_data\    → 工具数据
D:\AUTO-EVO-AI-V0.1\core\    → 数据库
```
直接复制备份即可。

---

> **技术支持：** 遇到任何问题，重启 `start.ps1` 即可恢复。
