# AUTO-EVO-AI 系统配置汇总

## 一、服务器

### 腾讯云（主站）
- **IP**: 122.51.144.227
- **用户**: ubuntu
- **密码**: Hj711201
- **端口**: 80/443（Nginx → 8765）
- **网站**: https://autoevoai.com
- **n8n**: https://autoevoai.com/n8n/
- **服务**: evo.service（FastAPI） + nginx + n8n
- **路径**: /home/ubuntu/my-evo-ai/
- **前端**: /home/ubuntu/my-evo-ai/frontend/

### 香港服务器（工具/CLI）
- **IP**: 43.129.75.222
- **用户**: ubuntu
- **密码**: Hj711201

## 二、GitHub
- **仓库**: https://github.com/haijun2024/autoevo-ai
- **本地**: D:/AUTO-EVO-AI-V0.1/
- **443不通**: 网络恢复后 git push 手动推送

## 三、本地开发环境
- **D 盘**: D:/AUTO-EVO-AI-V0.1/（Git 工作目录）
- **E 盘**: E:/AUTO-EVO-AI-V0.1/（robocopy 同步目标）
- **同步命令**: robocopy D:\AUTO-EVO-AI-V0.1 E:\AUTO-EVO-AI-V0.1 /MIR /COPYALL

## 四、AI 模型

### AutoDL（RTX 5090）
- **地址**: connect.westc.seetacloud.com:19126
- **用户/密码**: root / inoPMdJJ6Wvw
- **模型**: Qwen3.6-35B GGUF（/root/autodl-tmp/qwen-gguf/）
- **API**: http://localhost:6006/v1/chat/completions
- **推理速度**: ~77 tokens/s

### API 后端
- **主模型**: 智谱 GLM-4-Flash（免费）
- **备用**: DeepSeek API

## 五、今日修复清单（29项已修，剩2项 — 暂缓）
- [x] routes_tool_execute.py 100工具后端
- [x] n8n 安装+服务化+nginx子路径
- [x] Goose v1.38.0
- [x] CLI 14/15工具（缺n8n在腾讯云）
- [x] nginx SSL修复
- [x] index.html SEO/OG/favicon
- [x] share.css 公共样式
- [x] 10个页面SEO更新
- [x] enterprise.html 拆分恢复
- [x] chat.html 颜色统一
- [x] _archive/桩模块清理
- [x] TODO/FIXME + 单元测试
- [x] GitHub push（5 commit）
- [ ] ~~双前端体系（架构级）~~ — 暂缓
- [ ] ~~GitHub 443不通（网络问题）~~ — 暂缓
