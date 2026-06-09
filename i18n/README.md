# 统一 i18n 系统说明

## 架构

AUTO-EVO-AI 采用**纯文件驱动**的 i18n 架构：

### 后端 API (`api/routes_i18n.py`)
- 提供 `/api/v1/i18n?lang=xx` 和 `/api/v1/i18n/langs` 端点
- **纯文件加载**：从 `i18n/*.json` 读取所有翻译，无内置硬编码
- 支持 `Accept-Language` 自动检测
- 当前支持 8 语言：zh-CN, en, ja, fr, es, pt, ru, ar

### 前端引擎 (`frontend/i18n.js`)
- 9 语言前端专用翻译（zh-CN, en, ja, ko, fr, es, pt, ru, ar）
- keys 前缀与后端不冲突（前端用短 key 如 title, greeting）
- 通过 `__(key)` 函数在 chat.html 中使用
- 保持前端独立渲染能力，不依赖后端 API

### JSON 文件 (`i18n/*.json`)
- 每个语言一个文件，key 以命名空间前缀组织（`nav.*`, `module.*`, `common.*` 等）
- 新增语言只需添加 `i18n/{lang}.json` 文件即可自动生效

## 语言覆盖

| 语言 | 代码 | 后端 JSON | 前端 i18n.js |
|------|------|-----------|--------------|
| 简体中文 | zh-CN | ✅ | ✅ |
| English | en | ✅ | ✅ |
| 日本語 | ja | ✅ | ✅ |
| 한국어 | ko | ❌ (新增) | ✅ |
| Français | fr | ✅ | ✅ |
| Español | es | ✅ | ✅ |
| Português | pt | ✅ | ✅ |
| Русский | ru | ✅ | ✅ |
| العربية | ar | ✅ | ✅ |

## 使用规则

- 前端页面优先使用 `frontend/i18n.js` 的 `__(key)` 函数
- 需要后端返回翻译的页面使用 `/api/v1/i18n` 端点
- 新增语言只需添加 `i18n/{lang}.json` 文件即可
- 如需新增前端翻译，同步更新 `frontend/i18n.js`
