# AUTO-EVO-AI API 文档

## 基础信息

- **Base URL**: `http://localhost:8765`
- **认证**: `X-API-Key` 请求头
- **格式**: JSON

## 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 系统状态、模块数 |
| GET | `/api/health` | 模块健康详情 |
| GET | `/api/production/readiness` | 生产就绪评估 |
| GET | `/api/module/quality` | 模块质量分级 |

## 调度器

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scheduler/status` | 调度器状态、任务数 |
| POST | `/api/scheduler/start` | 启动调度器 |
| POST | `/api/scheduler/stop` | 停止调度器 |

## LLM

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/llm/providers` | 查看可用模型 |
| POST | `/api/setup/llm/quick-start` | 一键配置 LLM |

## 通知

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notify/channels` | 查看通知通道列表 |
| POST | `/api/setup/notify/quick-start` | 一键配置通知 |

## 安全

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/security/status` | 安全状态概览 |

## 智能化

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/autonomous/status` | 自主智能体状态 |

## i18n

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/i18n/status` | i18n 服务状态 |

## 前端页面

| 路径 | 说明 |
|------|------|
| `/dashboard` | 原始 Dashboard |
| `/wizard` | 3 步设置向导 |
| `/ops` | 运营中心 |
| `/docs` | Swagger API 文档 |
