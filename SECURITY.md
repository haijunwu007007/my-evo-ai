# 安全策略

## 报告漏洞

如果您发现 AUTO-EVO-AI 存在安全漏洞，请**不要**在 GitHub Issues 中公开报告。

请通过以下方式私下报告：

- 发送邮件至：GitHub Issues 中联系 @haijunwu007007
- 或直接在 GitHub 上创建 Security Advisory：
  `https://github.com/haijunwu007007/my-evo-ai/security/advisories`

## 响应时间

- 确认收到报告：48 小时内
- 初步评估：5 个工作日内
- 修复时间取决于严重程度

## 安全最佳实践

### 部署前必做

1. **设置环境变量**：`EVO_AUTH_SECRET`、`EVO_ADMIN_KEY` 必须设置为强随机值
2. **启用认证**：设置 `EVO_AUTH_ENABLED=true`
3. **更改默认端口**：不建议使用默认 8765 端口暴露到公网
4. **使用 HTTPS**：生产环境务必配置 TLS

### 依赖安全

- 定期运行 `pip audit` 检查 Python 依赖漏洞
- 前端依赖通过 `npm audit` 检查

## 受支持版本

| 版本 | 支持状态 |
|------|----------|
| V0.1 | ✅ 活跃开发中 |
