# 贡献指南 — AUTO-EVO-AI V0.1

> 上市公司级生产力标准。所有代码必须通过全链路验证方可合入。

## 代码标准

### 通用要求
- Python >=3.11，使用 `from __future__ import annotations` 启用延迟求值
- 所有函数/方法必须有类型注解（type hints）
- 所有 public 方法必须有 docstring（中英均可，但参数描述需完整）
- 不允许 `except: pass`，必须捕获具体异常
- 不允许硬编码路径/密钥，使用 `os.environ.get()` 或配置文件

### 模块开发规范

每个模块必须实现以下接口：

```python
from core.module_base import EvoModule

class MyModule(EvoModule):
    def __init__(self):
        super().__init__()
        self._repos = []          # 模块数据
        self._initialized = False # 初始化状态

    def initialize(self):
        """模块初始化 — 首次加载时调用"""
        self._initialized = True

    async def execute(self, action: str, params: dict = None, **kwargs) -> dict:
        """执行模块动作"""
        if action == "my_action":
            return self._do_thing(params)
        return {"success": False, "error": f"Unknown action: {action}"}

    def shutdown(self):
        """模块卸载时清理"""
        self._repos.clear()
```

### 调度任务模板

在 `api/_data_store.py` 的 `_TASK_TEMPLATES` 中添加：

```python
"my_task": {
    "name": "📊 我的任务",
    "desc": "任务描述",
    "steps": [{"module":"my_module","action":"my_action","params":{}}],
}
```

## 测试要求

### 必须覆盖
- 模块关键路径（每个 action 至少一个用例）
- 边界条件（空值、异常输入）
- `language='all'` 场景（不要过滤空字符串）

### 运行测试
```bash
# 独立测试
python -m pytest tests/test_my_module.py -v

# 全量验证
python -m pytest tests/ -q --tb=short
```

测试必须在提交前全绿通过。**不允许提交未通过测试的代码。**

## 提交流程

```bash
# 1. 从 master 分支
git checkout master && git pull

# 2. 创建功能分支
git checkout -b feat/my-feature

# 3. 编写代码 + 测试

# 4. 运行全量测试
python -m pytest tests/ -q --tb=short

# 5. 提交
git add -A
git commit -m "类型: 一句话描述改动"
git push origin feat/my-feature
```

## 代码审查清单

PR 合并前必须通过：
- [ ] 全量测试绿色（0失败 0告警）
- [ ] 类型注解完整
- [ ] 无 `except: pass` 或 `# type: ignore`
- [ ] 无硬编码密钥/路径
- [ ] 新增功能有对应测试
- [ ] README 或文档已同步更新

## 版本号约定

`v{MAJOR}.{MINOR}.{PATCH}`
- MAJOR: 架构/API 不兼容变更
- MINOR: 新增功能，向后兼容
- PATCH: bug 修复，向后兼容

## 联系

问题/讨论 → GitHub Issues
紧急 → @haijunwu007007
