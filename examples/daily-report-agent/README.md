# 📋 每日日报 Agent — 完整用例

> 演示如何用 AUTO-EVO-AI 调度多个模块协同完成真实任务。

## 场景

每天早上自动完成：
1. 扫描 GitHub 今日热门 Python 项目
2. 调用自我进化模块分析趋势
3. 生成结构化日报
4. 通过钉钉推送到团队群

## 一键部署

```bash
# 确保系统正在运行
python api_server.py

# 创建日报任务
curl -X POST http://127.0.0.1:8765/api/templates/github_trending/apply

# 查看已创建的任务
curl http://127.0.0.1:8765/api/scheduler/tasks
```

## 手动调用各模块

### 1. 扫描 GitHub 趋势
```python
import requests
r = requests.post("http://127.0.0.1:8765/api/coordinator/execute",
    json={"task": "扫描今日GitHub热门项目"})
print(r.json())
```

### 2. 分析趋势数据
```python
r = requests.post("http://127.0.0.1:8765/api/coordinator/execute",
    json={"task": "分析Python AI项目趋势"})
print(r.json())
```

### 3. 查看进化报告
```bash
curl http://127.0.0.1:8765/api/insights/evolution
```

## 效果

```
📊 GitHub 趋势日报 — 2026-05-24
━━━━━━━━━━━━━━━━━━━━━━━
🏆 Top 1: FoundZiGu/GuJumpgate (2103⭐)
   JavaScript — 今日最热

🏆 Top 2: sapientinc/HRM-Text (683⭐)
   Python — AI 文本处理

📈 趋势: AI/ML 项目占比 28%
选摘项目 25 个，覆盖 9 种语言
```

## 技术原理

1. `githubtrending` 模块: Search API 获取 7天内 50⭐以上项目
2. `self_evolution_reporter`: 分析趋势→分类→统计
3. `notifier`: 钉钉 webhook 推送结果（需配置 `DINGTALK_WEBHOOK`）
4. `scheduler_engine`: cron 调度每天 9:00 执行
