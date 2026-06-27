---
name: pixelrag
display_name: PixelRAG
description: 像素原生搜索RAG方案，将文档渲染为图像直接检索，解决传统文本解析视觉信息丢失问题
version: 1.0.0
grade: A
category: rag
stars: 3037
language: Python
source: https://github.com/StarTrail-org/PixelRAG
added_date: 2026-06-22
trending_rank: 6
scanner: github-ai-2
tags:
  - RAG
  - multimodal
  - vision-retrieval
  - pixel-native
  - document-search
---

# PixelRAG - 像素原生RAG方案

## 项目概述
**PixelRAG** 是 StarTrail-org 开源的像素原生搜索RAG方案，核心创新是将文档渲染为图像后直接检索，跳过传统文本解析流程，从根本上解决PDF/扫描件/复杂排版文档中视觉信息（表格、公式、图表、版式）丢失的痛点。

## 核心特性
| 特性 | 描述 |
|------|------|
| 像素原生 | 文档→图像→直接检索，零文本解析损失 |
| 多模态兼容 | PDF/扫描件/图片/复杂排版均适用 |
| 视觉信息保真 | 表格/公式/图表/版式完整保留 |
| 检索效率 | 亚秒级响应，适合大规模文档库 |
| 集成友好 | 提供Python API，可对接LangChain/LlamaIndex |

## 适用场景
- 法律/金融/医疗等专业领域文档检索
- 扫描件PDF/古籍/手写文档数字化检索
- 含复杂表格公式的技术文档
- 需要保留版式信息的合同/票据检索
- 多语言/特殊符号混排文档

## 集成方式
```python
from pixelrag import PixelRAG
rag = PixelRAG()
rag.add_documents(["doc1.pdf", "doc2.png"])
results = rag.search("查询内容", top_k=5)
```

## 评分理由
- **A级**：解决RAG领域核心痛点（视觉信息丢失），创新性强
- 3037 Star 表明获得社区关注
- 文档完整、API清晰
- 对企业级RAG系统具有显著提升价值
