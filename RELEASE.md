# AUTO-EVO-AI 发布流程

## 版本格式

`v{MAJOR}.{MINOR}.{PATCH}`

- **MAJOR**: 不兼容的 API/架构变更
- **MINOR**: 向下兼容的新功能
- **PATCH**: 向下兼容的缺陷修复

## 发布步骤

### 1. 创建版本 Tag

```bash
# 查看当前版本
git tag -l

# 打出新标签
git tag -a v0.1.1 -m "v0.1.1 - 修复: 模块加载/路由注册/部署脚本"

# 推送标签到 GitHub
git push origin v0.1.1
```

### 2. 生成 Changelog

```bash
git log --oneline --no-decorate v0.1.0..HEAD > CHANGELOG.md
```

### 3. 同步到所有环境

```bash
# E 盘
robocopy D:\AUTO-EVO-AI-V0.1 E:\AUTO-EVO-AI-V0.1 /MIR /XD .git _deps node_modules __pycache__ .pytest_cache .venv .workbuddy output apps specs _archive

# 云服务器
cd /home/ubuntu/my-evo-ai && git pull

# 重启
sudo systemctl restart evo-api
# 或 nohup 方式：
# pkill -f uvicorn
# nohup venv/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8765 > ~/evo.log 2>&1 &

# 验证
curl http://localhost:8765/api/v1/status
```

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1.0 | 2026-06-09 | 初始版本 |
