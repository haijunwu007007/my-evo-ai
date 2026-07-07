# AUTO-EVO-AI V0.1 — 系统简介

## 概述
AUTO-EVO-AI 是一个全栈 AI 自动化编排系统，集成了 LLM 对话、文档生成、代码辅助、数据搜索、桌面自动化、定时任务等 40+ 项核心能力。

## 核心功能
- **智能聊天**: 支持 GLM-4/OpenAI/DeepSeek 等多模型，有真实 LLM 能力
- **文档生成**: 支持 Word/PPT/Excel 三种格式的本地生成
- **代码辅助**: Python/JS/SQL/Java 代码生成与解释
- **GitHub 热门查询**: 实时获取 GitHub Trending 项目数据
- **网页搜索**: 通过 DuckDuckGo 实时搜索互联网
- **网页爬虫**: 基于 crawl4ai 的 AI 网页内容抓取
- **数学计算**: 本地表达式计算引擎
- **持久记忆**: SQLite 存储用户记忆
- **待办管理**: 创建/查询/完成的待办 CRUD 系统
- **桌面自动化**: pyautogui 截图/打开应用
- **定时任务**: 支持 Cron 表达式调度
- **翻译**: 9种语言互译
- **多语言界面**: 中文/English/日本語/한국어/Français/Español/Português/Русский/العربية

## 技术栈
- 后端: FastAPI + Python 3.13
- 前端: 纯 HTML/CSS/JS 零依赖
- 数据库: SQLite
- LLM: GLM-4-Flash (智谱)
- 446+ 模块的懒加载架构
