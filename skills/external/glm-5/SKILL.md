---
name: glm-5
version: 0.1.0
grade: A
stars: 5077
language: Python
added: 2026-06-22
source: ngjoo-daily
url: https://github.com/zai-org/GLM-5
tags: [llm, foundation-model, glm, zhipu, agent-model]
---

# GLM-5 — 智谱第五代基座模型

智谱 AI 2026 年开源的最新一代基座模型（zai-org/GLM-5），5k Star，194 日增。中文场景下与 GPT/Claude 同级竞争力。

## 核心能力
- 第 5 代基座（GLM-1/2/3/4 → 5）
- 中英双语 SOTA
- 128K 上下文
- Tool Use / Function Call 原生支持
- 量化版本：BF16 / INT8 / INT4

## 适用场景
- 替代 GPT-4 / Claude-Sonnet 的中文 LLM 选项
- AUTO-EVO-AI 主对话模型（国产化部署）
- 智谱 BigModel 平台 API 兜底

## 与 AUTO-EVO-AI 集成点
- 替换/补充 `llm_zhipu.py`
- 与 `qwen3.6` 形成国产模型双路由
- 适合 `glossary` / `rag` 等中文场景
