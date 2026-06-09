# AUTO-EVO-AI 技能系统

AUTO-EVO-AI 内置了完整的技能（Skill）体系，支持用户通过自然语言直接调用系统功能。

## 技能目录结构

```
skills/
├── SKILL_CONTRACT.md     # 技能合约规范
├── Skills.md             # 本文档
├── builtin/              # 内置技能（18个）
│   ├── text/             # 文本处理
│   ├── document/         # 文档生成
│   ├── code/             # 代码生成
│   ├── image/            # 图片处理
│   ├── search/           # 搜索
│   ├── crawl/            # 爬虫
│   ├── translate/        # 翻译
│   ├── calculator/       # 计算
│   ├── github/           # GitHub工具
│   ├── memory/           # 记忆管理
│   ├── todo/             # 待办管理
│   ├── ppt/              # PPT生成
│   ├── excel/            # Excel处理
│   ├── voice/            # 语音
│   ├── screenshot/       # 截图
│   ├── scaffold/         # 脚手架
│   ├── docker/           # Docker
│   └── app_launcher/     # 应用启动
├── custom/               # 自定义技能
└── auto-discovered/      # WorkBuddy自动发现的外部技能
```

## 技能总数

| 类型 | 数量 |
|------|------|
| 内置技能 | 18 |
| 自定义技能 | 可变 |
| WorkBuddy外部技能 | 28+ |
| MCP桥接工具 | 8+ |
| 连接器集成 | 101+ |
| **总计** | **156+** |

## 使用方法

在聊天窗口输入以下关键词即可调用：
- "有哪些技能" — 列出所有可用技能
- "帮我写合同" → word_create 技能
- "做个表格" → excel_write 技能
- "翻译成英文" → translate 技能
- 更多技能详见 skills/builtin/ 目录
