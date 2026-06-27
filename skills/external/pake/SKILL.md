---
name: pake
version: 0.1.0
grade: A+
stars: 56199
language: Rust
added: 2026-06-22
source: wangchujiang-weekly
url: https://github.com/tw93/Pake
tags: [desktop-app, rust, tauri, webview, productivity]
---

# Pake — 一行命令将网页变成桌面应用

By **tw93**，56k Star，1848 日增。基于 Tauri + Rust 把任何网页打包为轻量级桌面应用（比 Electron 小 20 倍，启动快 5 倍）。

## 核心能力
- 一行 CLI 命令：`pake https://example.com`
- Tauri 引擎（Rust + 系统 WebView）
- 体积仅 5MB（vs Electron 100MB+）
- 启动 < 1s
- 支持自定义窗口样式 / 注入 JS

## 适用场景
- 把 Web 工具封装为桌面端
- AUTO-EVO-AI 前端 → 桌面端打包
- 离线工具 / 内网应用容器化

## 与 AUTO-EVO-AI 集成点
- 将 chat.html / dashboard.html 打包为 PWA + 桌面端
- 利用 Tauri 减少前端体积
