# AUTO-EVO-AI Skill 标准化接口

## 什么是 Skill

Skill 是 AUTO-EVO-AI 系统中**最小的可执行能力单元**。每个 Skill 是一个独立的功能模块，有标准的输入/输出定义，可以被聊天、Workflow、API 三种方式调用。

## SKILL.md 定义格式

每个 Skill 目录下必须有 `SKILL.md` 作为声明文件：

```markdown
---
name: "document-generator"
version: "1.0.0"
description: "生成 Word/PDF/Markdown 文档"
author: "AUTO-EVO-AI"
category: "文件生成"
icon: "📝"
tags: ["文档", "Word", "合同", "方案"]
input_schema:
  type: object
  properties:
    content:
      type: string
      description: "文档内容"
    format:
      type: string
      enum: [docx, md, txt]
      default: docx
output_schema:
  type: object
  properties:
    file_path:
      type: string
      description: "生成的文件路径"
    format:
      type: string
---

# 文档生成器

生成各类 Word/Markdown/TXT 文档。

## 使用方式
- 聊天: "帮我写一份合同" 或 "生成Word文档"
- Workflow: 作为"文档生成"节点拖入画布
- API: POST /api/v1/skills/document-generator/execute

## 示例
```
{
  "content": "合同内容...",
  "format": "docx"
}
```
```

## API 接口

### 注册 Skill
```
POST /api/v1/skills/register
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "...",
  "input_schema": {...},
  "handler": "my_package.my_function"
}
```

### 列出所有 Skill
```
GET /api/v1/skills
```

### 获取单个 Skill 详情
```
GET /api/v1/skills/{name}
```

### 执行 Skill
```
POST /api/v1/skills/{name}/execute
{
  "params": {...}
}
```

### 搜索 Skill
```
GET /api/v1/skills/search?q=文档
```

## 内置 Skill 列表

| 名称 | 分类 | 说明 |
|------|------|------|
| text-generator | 文本生成 | 文章/报告/创意写作 |
| document-generator | 文档生成 | Word/合同/方案 |
| code-generator | 代码生成 | Python/JS/SQL/Java |
| image-generator | 图片生成 | AI 绘图 |
| search-web | 网页搜索 | DuckDuckGo 实时搜索 |
| web-crawler | 网页爬虫 | crawl4ai 结构化抓取 |
| translate | 翻译 | 9 种语言互译 |
| math-calculator | 数学计算 | 公式/表达式计算 |
| github-trending | GitHub 热门 | 实时 TOP 10 |
| memory-save | 持久记忆 | 记住/回忆信息 |
| todo-manager | 待办管理 | 创建/查询/完成 |
| ppt-generator | PPT 生成 | 演示文稿 |
| excel-generator | Excel 生成 | 数据表格 |
| voice-tts | 语音合成 | 文本转 mp3 |
| desktop-screenshot | 桌面截图 | 截取屏幕 |
| docker-deploy | Docker 部署 | 容器编排 |
| project-scaffold | 项目脚手架 | 快速创建项目 |

## 自定义 Skill

把 SKILL.md 和执行脚本放入 `skills/custom/{name}/` 目录，然后调用：
```
POST /api/v1/skills/register
```

系统会自动检测目录变化并注册。
