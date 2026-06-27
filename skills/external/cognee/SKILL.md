---
name: cognee
version: 0.1.0
grade: A
stars: 18639
language: Python
added: 2026-06-22
source: wangchujiang-weekly
url: https://github.com/topoteretes/cognee
tags: [agent-memory, knowledge-graph, rag, memory-engine, ai-memory]
---

# Cognee — 开源 AI Agent 长期记忆平台

18k Star，347 日增。借助自托管知识图谱引擎，为 AI Agent 提供**跨会话的持久长期记忆**。

## 核心能力
- 自托管知识图谱引擎（基于 Neo4j / Memgraph / LanceDB）
- 跨会话 Agent 记忆
- 文本 / PDF / 图片 / 音频多模态摄入
- 时序记忆 + 实体关系抽取
- 与 LangChain / LlamaIndex / Claude / OpenAI 集成

## 适用场景
- AI Agent 长期记忆基础设施
- RAG 知识库增强（图谱 vs 向量）
- 客户对话历史沉淀

## 与 AUTO-EVO-AI 集成点
- 替代/补充 `mempalace` / `mem0`
- 增强 `claude-mem` 记忆图谱能力
- 作为 `RAG` 系统的图谱后端
