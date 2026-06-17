# AUTO-EVO-AI 测试指南

## 运行测试

```bash
# 运行全部测试
pytest tests/ -v --tb=short

# 运行特定测试文件
pytest tests/test_database.py -v
pytest tests/test_agent_tools.py -v

# 带覆盖率
pytest tests/ --cov=api --cov-report=term
```

## 测试架构

```
tests/
├── __init__.py          # 测试包入口
├── test_agent_tools.py  # 工具注册与执行测试
└── test_database.py     # SQLite 数据库层测试
```

## 添加新测试

```python
def test_my_feature():
    from api.my_module import my_func
    result = my_func()
    assert result["ok"] == True
```
