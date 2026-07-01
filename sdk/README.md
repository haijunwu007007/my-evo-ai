# AUTO-EVO-AI SDK

## Python

```python
from evoclient import EvoClient

c = EvoClient()  # 默认连接 https://autoevoai.com

# 对话
print(c.chat("你好"))
# 模块列表  
print(c.modules("AI & Agent"))
# 技能
print(c.skills())
# 系统状态
print(c.status())
```

## JavaScript

```javascript
const { EvoClient } = require('./evoclient.js');
const c = new EvoClient();

const res = await c.chat('生成一份合同');
console.log(res.data);
```

## API 文档

完整 API 参考：https://autoevoai.com/docs
