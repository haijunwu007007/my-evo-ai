---
name: ppt-master
display_name: PPT Master
description: AI从任意文档生成原生可编辑PowerPoint——真正的形状、文本框、图表（非截图）
version: 1.0.0
grade: A+
category: office
stars: 30183
language: Python
source: https://github.com/hugohe3/ppt-master
added_date: 2026-06-22
trending_rank: 18
scanner: github-ai-2
tags:
  - powerpoint
  - document-generation
  - office-automation
  - native-format
  - ai-presentation
---

# PPT Master - 文档→原生可编辑PPT

## 项目概述
**PPT Master** 是 hugohe3 开源的AI演示文稿生成工具，核心能力是从任意文档（PDF/Word/Markdown/网页）直接生成 **原生PowerPoint格式**，包含真实的形状、文本框、图表、SmartArt，而非低质量的截图或图片占位。

## 核心特性
| 特性 | 描述 |
|------|------|
| 原生PPTX | 输出真正可编辑的PowerPoint文件 |
| 结构识别 | 自动解析文档层级/标题/列表/表格 |
| 智能布局 | 根据内容语义选择最适幻灯片版式 |
| 图表生成 | 自动生成可编辑的原生图表（柱状/折线/饼图）|
| 主题适配 | 支持自定义企业VI/配色/字体 |
| 批量生成 | 一次性处理多文档输出统一风格PPT |

## 适用场景
- 企业报告/周报/月报自动化生成
- 学术论文→答辩PPT转换
- 商业计划书/产品介绍PPT快速产出
- 培训材料批量制作
- 营销方案/产品手册可视化

## 使用方式
```python
from pptmaster import Generator
gen = Generator(template="corporate")
ppt = gen.from_document("report.pdf", output="report.pptx")
```

## 评分理由
- **A+级**：填补AI生成PPT只能产截图的空白
- 30183 Star，NGJOO日榜Top 18
- 原生格式输出对Office生态友好
- 商业落地价值极高，节省人工排版时间90%+
