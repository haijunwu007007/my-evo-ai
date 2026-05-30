# AUTO-EVO-AI V0.1 API 文档

## 基础信息
- **Base URL**: `http://localhost:8765`
- **Swagger UI**: `/docs`
- **OpenAPI JSON**: `/openapi.json`
- **认证方式**: JWT Bearer Token（`/api/auth/login` 获取）

## 核心端点

### 🔧 系统管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 系统运行状态、模块数、版本 |
| `/api/diagnosis/system` | GET | 系统诊断（运行时长/内存/CPU） |
| `/api/diagnosis/modules` | GET | 模块诊断 |
| `/api/system/metrics` | GET | 系统指标（请求数/错误率） |
| `/api/monitor/realtime` | GET | 实时监控（CPU/内存/磁盘/网络） |

### 📦 模块管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/modules` | GET | 模块列表（支持搜索/分级/分页） |
| `/api/modules/categories` | GET | 模块分类统计 |
| `/api/modules/rescan` | POST | 重新扫描模块目录 |
| `/api/modules/{name}` | GET | 模块详情 |
| `/api/modules/{name}/execute` | POST | 执行模块动作 |

### 📅 调度器
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/scheduler/status` | GET | 调度器状态 |
| `/api/scheduler/tasks` | GET | 调度任务列表 |
| `/api/scheduler/tasks` | POST | 创建调度任务 |
| `/api/scheduler/tasks/{id}/toggle` | POST | 切换任务启用状态 |

### 📊 数据分析
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/events/stats` | GET | 事件统计 |
| `/api/events/rules` | GET | 事件规则列表 |
| `/api/pipelines` | GET | 管线列表 |
| `/api/queue/stats` | GET | 队列统计 |
| `/api/queue/tasks` | GET | 队列任务 |

### 🔐 认证
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录（返回JWT） |
| `/api/auth/status` | GET | 认证状态 |
| `/api/auth/logout` | POST | 登出 |

### ⚙️ 配置
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/config` | GET | 全部配置 |
| `/api/config/{key}` | GET | 指定配置项 |
| `/api/config/{key}` | PUT | 更新配置 |
| `/api/config/batch` | POST | 批量更新 |

### 🧠 协调中心
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/coordinator/status` | GET | 协调器状态 |
| `/api/coordinator/capabilities` | GET | 协调能力列表 |
| `/api/coordinator/execute` | POST | 执行协调任务 |

## 数据格式

### 统一响应格式
```json
{
  "success": true,
  "error": null,
  "message": null,
  "data": {}
}
```

### 模块对象
```json
{
  "name": "system_monitor",
  "file": "system_monitor.py",
  "size": 28118,
  "lines": 680,
  "grade": "A",
  "category": "SYSTEM",
  "real_logic": true,
  "actions": ["execute"],
  "docstring": "模块描述..."
}
```

## 快速使用

```bash
# 1. 获取认证token
curl -X POST http://localhost:8765/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "api_key": "your-api-key"}'

# 2. 查看系统状态
curl http://localhost:8765/api/status

# 3. 列出模块
curl "http://localhost:8765/api/modules?page=1&page_size=10"

# 4. 执行模块
curl -X POST http://localhost:8765/api/modules/system_monitor/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "get_metrics", "params": {}}'
```
