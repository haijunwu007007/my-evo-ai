---
name: ai-website-cloner-template
display_name: AI Website Cloner - 一键克隆网站到Next.js
description: 用一条命令把任意网站逆向工程为现代化 Next.js 代码库。5阶段管道 + Spec契约 + Git Worktree并行，专为 Claude Code 等 AI 编码代理设计
version: 1.0.0
stars: 15700
category: ai-coding
language: typescript
license: MIT
source: https://github.com/JCodesMore/ai-website-cloner-template
auto_discovered: 2026-06-23
discovered_by: github-ai-scanner
grade: A
status: active
trending_score: 82
tags: [website-clone, nextjs, reverse-engineering, ai-coding-agent, 5-stage-pipeline]
---

# AI Website Cloner Template

## 简介

AI Website Cloner Template 是一个可复用的模板，让 AI 编码代理 (Claude Code/Cursor/Copilot) 通过一条命令就能把任意网站逆向工程成现代化 Next.js 代码库。5 阶段管道 + Spec 文件契约 + Git Worktree 并行构建。

## 核心数据

- **GitHub Stars**: 15,672+
- **语言**: TypeScript
- **协议**: MIT
- **发布**: 2026-03-28
- **更新**: 2026-05-07 (持续活跃)

## 5 阶段管道

1. **Reconnaissance (侦察)** - 抓取目标站结构、样式、行为
2. **Setup (搭建)** - 初始化 Next.js 16 代码库、配置
3. **Specification (规范)** - 生成 Spec 文件作为契约
4. **Parallel Build (并行构建)** - 用 Git Worktree 多 Agent 并行开发
5. **QA & Deploy (质检+部署)** - 自动测试 + 一键部署

## 适用场景

1. **快速复刻参考站** - 学习优秀产品的实现
2. **私有化白标** - 把 SaaS 产品包装为自有品牌
3. **离线备份** - 把关键文档/产品页本地化
4. **MCP 集成** - 给 AI 助手加"克隆网站"能力
5. **设计系统提取** - 自动抽取设计规范

## 与本系统集成

- 与 `mcpize` 互补 (后者是 REST/网站→MCP 工具，此项目是 Next.js 复刻)
- 与 `firecrawl` 互补 (后者爬取数据，前者复刻外观)
- 用户在 `smart_chat` 说"克隆这个网站"时激活

## 引用

- 仓库: https://github.com/JCodesMore/ai-website-cloner-template
- 架构拆解: https://txtmix.com/posts/tech/jcodesmore-ai-website-cloner-template-agent-skill-architecture/
- 上手指南: https://cloud.tencent.com/developer/article/2651790
