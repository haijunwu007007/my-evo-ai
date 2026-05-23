# AUTO-EVO-AI 学习引擎

## 架构

执行日志 → 分析 → 洞察 → 自动优化 → 学习规则库

## 自动分析维度

1. **性能**：识别 >5s 的慢模块，建议优化方向
2. **错误率**：追踪高频失败模块，自动添加重试机制
3. **空跑检测**：识别产出为零的调度任务，建议降低频率

## API

```
GET  /api/learning/analyze    - 分析执行日志
POST /api/learning/optimize   - 手动触发自动优化
GET  /api/learning/report     - 学习报告
```

## 数据存储

`data/learning_rules.json` - 自动积累优化规则，重启不丢失
