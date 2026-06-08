# 模块调用指南 — Module Calling Guide

> 让 LLM 智能体准确调用 457 个系统模块的完整指南

## 核心流程

```
用户需求 → 搜索模块 → 查看模块示例 → 调用模块 → 组合结果
```

## 模块发现

### 1. 搜索模块

使用 `search_modules` 工具按中文关键词搜索模块：

```
search_modules(keyword="报名")
```

返回结果包含模块路径、文件大小、质量等级（🟢真实/🟡桩）和功能描述。

### 2. 查看模块详情

使用 `module_info` 工具查看模块的详细信息和调用示例：

```
module_info(module="form_builder")
```

返回：模块描述、参数结构、execute() 方法签名、自动生成的调用示例。

## 模块调用

### 3. 调用模块

使用 `execute_module` 工具调用模块：

```
execute_module(module="form_builder", action="execute", params='{"name":"测试表单"}')
```

参数说明：
- `module`: 模块名（必填）
- `action`: 执行动作（必填），通常为 "execute"
- `params`: JSON 字符串参数（可选）

### 4. 查看模块列表

使用 `list_modules` 查看系统所有模块的分类统计：

```
list_modules()
```

返回各类别模块数量和质量分布。

## 参数规范

每个模块的 `execute()` 方法接收：
- `action: str` — 执行动作
- `params: Optional[Dict]` — 参数字典

对于 EnterpriseModule 基类模块，额外支持：
- `action="status"` — 查看模块状态
- `action="config"` — 获取配置信息
- `action="metrics"` — 查看性能指标

## 智能匹配

系统会自动将用户需求匹配到相关模块：

```
用户说"开发一个报名系统"
  → 协调器搜索含 form/注册/用户 关键词的模块
  → 返回 form_builder, auth_manager, user_profile 等
  → LLM 选择最合适的模块调用
```

匹配优先级：
1. 协调器能力图谱（语义匹配）
2. 关键词映射（中文→英文模块名）
3. 模块文件内容搜索

## 最佳实践

### 开发任务优先用模块

```
✅ 正确: 先 search_modules 找相关模块，再用 execute_module 调用
❌ 错误: 直接 file_write 写代码，忽略已有模块
```

### 复杂任务组合多个模块

```
1. search_modules → 找到 form_builder + database_manager + user_profile
2. module_info → 查看每个模块的调用示例
3. execute_module → 依次调用各模块
4. file_write → 组合模块输出为完整页面
```

### 模块质量判断

- **🟢 真实模块**: >2KB 且有 execute() 方法，可直接调用
- **🟡 桩模块**: <2KB 或无 execute()，功能有限

目前 457 个模块中 99.3% 为真实模块。

## 常见问题

### Q: 模块返回失败怎么办？
A: 检查参数格式是否正确，尝试调用 `execute_module(module="xxx", action="status")` 先查看模块状态。

### Q: 不知道模块需要什么参数？
A: 先用 `module_info` 查看模块详情，它会自动分析模块代码并生成调用示例。

### Q: 模块不存在？
A: 尝试用 `search_modules` 搜索相近关键词，或直接用 `file_write` 生成代码。

---

*本文档由 AUTO-EVO-AI 自动生成，持续更新。*
