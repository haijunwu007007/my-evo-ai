# 开源中心 · 可视化操作规范（精装版）

> **可视化的增·删·合·并·改·二次三次开发**
> 普通用户像操作画板一样操控整个开源世界

---

## 一、工作区 · 核心界面

```
┌────────────────────────────────────────────────────────────────┐
│  [💡 发现] [📦 我的项目] [🧬 衍生中心] [📊 监控]  [👤 用户]  │
├───────────┬────────────────────────────────────────────────────┤
│  项目面板  │                   主画布                           │
│  ┌──────┐ │  ┌──────────────────────────────────────────────┐  │
│  │ 搜索  │ │  │                                              │  │
│  │ ───── │ │  │    ┌──────┐         ┌──────┐                 │  │
│  │ AI    │ │  │    │Ollama│────────▶│WebUI │                 │  │
│  │ 工具  │ │  │    └──────┘         └──────┘                 │  │
│  │ ───── │ │  │        │                                      │  │
│  │ Web   │ │  │        ▼                                      │  │
│  │ 应用  │ │  │    ┌──────┐         ┌──────────┐             │  │
│  │ ───── │ │  │    │Dify  │────────▶│MyChat ❄️  │             │  │
│  │ 数据  │ │  │    └──────┘         └──────────┘             │  │
│  │ ───── │ │  │                                              │  │
│  │ 更多  │ │  │    ┌──────────────────┐                       │  │
│  │       │ │  │    │  NocoDB          │                       │  │
│  └──────┘ │  │    └──────────────────┘                       │  │
│           │  └──────────────────────────────────────────────┘  │
│  右键菜单  │                                                    │
│  ┌──────┐ │  左下角: [⚡资源池: CPU 45% 内存 62% 磁盘 120G]     │
│  │ 停用  │ │                                                    │
│  │ 修改  │ │                                                    │
│  │ 二次  │ │                                                    │
│  │ 开发  │ │                                                    │
│  │ 删除  │ │                                                    │
│  └──────┘ │                                                    │
└───────────┴────────────────────────────────────────────────────┘
```

---

## 二、五步核心流程详解

### 第一步：🧩 增加（Add）

**用户视角**：
```
① 打开「发现」→ 看到瀑布流卡片（GitHub Trending/HuggingFace/更多源）
② 每个卡片显示：项目名/⭐星数/一句话描述/类别标签/技术栈图标
③ 鼠标悬停 → 卡片浮起 → 显色「快速查看」+「加入工作区」两个按钮
④ 点「加入工作区」→ 项目以节点形式出现在主画布
⑤ 也可直接「拖拽」卡片到画布 → 自动创建节点
⑥ 不离开页面，毫无打断感
```

**系统后台同时开始**：
```
① 分析项目依赖（requirements.txt/package.json/Dockerfile）
② 检测运行时要求（Python版本/Node版本/GPU要求）
③ 检查端口占用（11434已占?→自动分配到11435）
④ 预下载（可选：用户能勾选"后台预下载"）
⑤ 画布节点显示实时状态: 分析中 ✓ → 就绪 ✓ → 运行中 ⚡
```

**节点在画布上的形态**：
```
┌─────────────────────────────────┐
│  Ollama                         │
│  🐳 Docker  •  AI推理引擎        │
│  ─────────────────────────────  │
│  ⚡ 运行中   📍 端口: 11435      │
│  📡 CPU:12%   🧠 内存: 1.2GB    │
│  ┌──────┐  ┌──────┐  ┌──────┐  │
│  │ 停用  │  │ 配置  │  │ 编辑  │  │
│  └──────┘  └──────┘  └──────┘  │
│  往右拖出连接线 → 连接到其他节点    │
└─────────────────────────────────┘
```

**添加的来源扩展**：
| 来源 | 方式 | 场景 |
|------|------|------|
| GitHub | 搜索/趋势/直接粘URL | 最常用 |
| HuggingFace | 搜索模型/Dataset/Space | AI项目 |
| Docker Hub | 搜索镜像名 | 容器化项目 |
| Git Code/Gitee | 国内镜像 | 国内加速 |
| 本地文件夹 | 拖拽上传/选择目录 | 已有项目 |
| 从模板库 | 社区模板菜单 | 快速开始 |
| 从URL | 粘贴git/下载链接 | 任意项目 |

**"智能添加"弹窗（首次加入时的配置）：**
```
┌─────────────────────────────────────────┐
│  加入 Ollama                            │
│                                         │
│  📦 所需磁盘: ~5GB                       │
│  🐳 部署方式: [Docker ✓] [直接安装]      │
│  📍 端口映射: 11435 → 11434 (容器内)     │
│  ⚙️ 环境变量: GPU支持 ✓ 开启             │
│  🏷️ 标签: AI推理  (可编辑)               │
│  🔗 挂载到Evo: /api/ollama ✓            │
│  ⏰ 超时: 60秒                           │
│                                         │
│  [简化/详细切换]  [取消]  [确认加入]       │
└─────────────────────────────────────────┘
```

---

### 第二步：✂️ 删除（Delete）

**四种删除深度，级联清理：**

```
右键菜单 → 删除 →
├─ 🛑 停用（保留数据和配置，下次秒启）
│  效果：节点变灰，服务停止
│  恢复：右键→启动
│
├─ 🗑️ 卸载（删除代码+数据，保留配置快照）
│  效果：节点移除 → 进入"已卸载"列表
│  恢复：从已卸载列表一键恢复
│
├─ 🔥 清理（卸载+清理依赖+Docker镜像，不可恢复）
│  效果：节点彻底移除
│  提醒框：将要释放 总共 5.2GB 磁盘空间 确认？
│
└─ 🧹 级联删除（删除本节点时，自动检查并清理无依赖的节点）
```

**智能删除提醒：**
```
┌─────────────────────────────────────────┐
│  删除 "WebUI" 将影响以下内容:            │
│                                         │
│  ⚠️  "MyChat" (二次开发) 依赖此项目       │
│     [同时删除] [仅解除依赖] [取消]        │
│                                         │
│  释放资源: 2.1GB磁盘 / 512MB内存         │
│  保留配置快照: ✓ 可恢复                   │
└─────────────────────────────────────────┘
```

---

### 第三步：🔗 组合/合并（Combine/Merge）

**组合操作（用户视角）：**
```
方式A: 拖拽连线
  从节点A的右侧「●」拖到节点B的左侧「●」
  → 看到蓝色连接线 → 松开 → 组合建立
  → 弹窗询问: A的输出传给B的输入? 确认

方式B: 框选合并
  在画布上拖拽矩形选择多个节点
  → 右键 → 「合并为新项目」
  → 弹出命名框: 新项目名称?
  → 确认 → 节点合并为一个分组框

方式C: 自动建议
  系统根据节点的API接口自动检测
  → "检测到 Ollama 和 Open WebUI 可以组合"
  → "一键组合为 AI聊天应用?"
```

**组合后的统一管理：**
```
┌───────────────────────────────────────────────┐
│  📦 我的AI平台 (组合项目)                       │
│  ┌──────────────────────────────────────────┐  │
│  │  ┌──────┐    ┌──────┐    ┌──────┐        │  │
│  │  │Ollama│───▶│WebUI │───▶│Dify  │        │  │
│  │  └──────┘    └──────┘    └──────┘        │  │
│  │                                          │  │
│  │  ⏺ 统一入口: http://localhost:3000/my-ai │  │
│  │  📊 总CPU: 45%  总内存: 2.1GB            │  │
│  │  [启动全部] [停止全部] [配置] [导出模板]     │  │
│  └──────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

**合并的三种形态：**

| 形态 | 连接方式 | 数据流 | 示例 |
|------|---------|--------|------|
| **串联 Pipeline** | A🔗B🔗C | A输出→B输入→C输出 | Ollama→翻译→语音输出 |
| **并联 Hub** | 统一入口→多服务 | 用户选哪个用哪个 | 聊天/绘图/搜索→统一面板 |
| **嵌套 Submodule** | A包含B | B作为A的插件运行 | Dify嵌入Ollama作推理引擎 |

**合并后的产物 → 成为「衍生项目」**：
```
组合保存后，自动创建为衍生项目
├─ 名称: 用户自定义
├─ 图标: 自动生成或用户选
├─ 版本: v1.0
├─ 基础: 基于 [Ollama + Open WebUI + Dify]
├─ 可导出: 导出为模板分享到社区
└─ 可部署: 一键启动全部子项目
```

---

### 第四步：✏️ 修改（Modify）

**四层修改，从简单到深入：**

**①🎨 配置级修改（所有人）：**
```
双击节点 → 属性面板打开 → 直接编辑
┌─────────────────────────────────┐
│  Ollama 属性                    │
│  ────────────────────────────  │
│  📍 端口: [11435     ] ← 直接改 │
│  ⚙️ 环境变量:                   │
│    OLLAMA_HOST = localhost     │
│    OLLAMA_PORT = 11435         │
│  🏷️ 标签: [AI推理  LLM]        │
│  🔗 路由路径: [/api/ollama   ]  │
│  🚀 启动命令: [... ]            │
│  ────────────────────────────  │
│  [重置默认] [保存] [对比原始]    │
└─────────────────────────────────┘
```

**② 🎨 外观级修改（所有人）：**
```
右键 → 修改 → 外观
┌─────────────────────────────────┐
│  修改项目外观                    │
│  ────────────────────────────  │
│  名称: [My Ollama        ]     │
│  图标: [🎯] 点击选择图标         │
│  颜色: [#6366f1] 点击选择颜色    │
│  描述: [我的定制推理引擎    ]    │
│  ────────────────────────────  │
│  [重置] [保存]                  │
└─────────────────────────────────┘
```

**③ 📝 代码级修改（进阶用户/开发者）：**
```
右键 → 修改 → 编辑源码
→ 内置浏览器版 VS Code（Code Server）打开项目目录
├─ 左侧: 文件树
├─ 中间: 代码编辑器（带语法高亮）
├─ 底部: 终端
├─ 右侧: AI助手聊天窗口
└─ 顶部工具栏:
   [保存] [撤销] [运行] [预览] [提交版本] [AI帮我改]
```

**④ 🔧 高级修改（添加/删除功能模块）：**
```
右键 → 修改 → 模块管理
→ 显示项目内部的组件/功能列表
├─ ✓ Main Chat (核心)
├─ ✓ User Login (模块)
├─ ✓ File Upload (模块)
├─ ☐ Voice Input (插件, 未安装)
├─ ☐ Dark Mode (插件, 未安装)
└─ [添加模块] [安装社区插件]
```

**版本历史管理：**
```
┌────────────────────────────────────┐
│  📋 修改历史 — MyChat              │
│                                    │
│  v1.3  │ 加中文翻译      │ 16日10:25│ ← 当前
│  v1.2  │ 改端口8080→80   │ 16日10:15│ ← 可回滚
│  v1.1  │ 改主题为暗黑    │ 16日09:30│
│  v1.0  │ 初始二次开发     │ 15日14:00│
│                                    │
│  [对比差异] [回滚到此版本] [导出]    │
└────────────────────────────────────┘
```

---

### 第五步：🧬 二次/三次/无限次开发（Fork & Evolve）

**核心机制：从「使用」到「创造」**

```
层级进化：
┌─ 原始开源项目 ──────────────────────────────┐
│  Open WebUI  v0.5.0 (社区开源项目)           │
│  ★ 12000  |  📝 开源许可证 MIT               │
└─────────────────┬───────────────────────────┘
                  │ 右键 → 「二次开发」
                  ▼
┌─ 二次开发: MyChat v1.0 ────────────────────┐
│  📦 基于: Open WebUI v0.5.0                │
│  ✏️ 修改: 主题UI + 中文翻译 + 移动端适配     │
│  🔗 可拉取上游更新                          │
│  ★ 独立管理，独立部署                       │
│  [继续三次开发] [打包分享]                   │
└─────────────────┬───────────────────────────┘
                  │ 「三次开发」
                  ▼
┌─ 三次开发: MyChat Pro v2.0 ───────────────┐
│  📦 基于: MyChat v1.0                      │
│  ✏️ 修改: 集成语音输入 + AI助手 + 插件系统   │
│  ★ 已偏离原始项目 65% 代码                  │
│  [发布到社区] [转为独立项目]                  │
└────────────────────────────────────────────┘
```

**二次开发的操作方式：**
```
右键项目节点 → 开发菜单 →
├─ 🚀 二次开发 (基于当前项目创建新分支)
│  → 自动Fork代码到独立目录
│  → 生成新的衍生项目条目
│  → 打开编辑器（Code Server），开始修改
│  → 修改自动保存为版本历史
│
├─ 🔄 拉取上游更新 (合并原始项目的新版本)
│  → 自动对比差异
│  → 显示冲突列表
│  → 逐项选择: 保留我的/采用上游/手动合并
│
├─ 📤 发布到社区 (分享你的衍生作品)
│  → 填写名称/描述/截图
│  → 选择许可协议
│  → 一键发布
│
└─ 📊 衍生树 (查看项目家族关系)
   → 显示完整的派生链条
   → 统计分支数量/衍生版本数
```

**衍生项目家族树视图：**
```
                    Open WebUI v0.5.0
                    ★ 12000 ⭐
                          │
          ┌───────────────┼───────────────┐
          │               │               │
     MyChat v1.0    WebUI-CN v1.0    AdminUI v1.0
     ★ 23 ⭐        ★ 15 ⭐          ★ 8 ⭐
          │
          │
     MyChat Pro v2.0
     ★ 12 ⭐
          │
          │
     MyChat Pro v3.0
     (含语音+AI助手)
```

**AI 辅助二次开发（内置能力）：**

```
用户说: "帮我加一个自动翻译功能"
   ↓
① AI 分析当前项目结构 → 定位相关文件
② 理解原始项目API → 找到翻译接口位置
③ 生成修改代码 → 展示修改预览
④ 用户确认 → 应用 → 保存为新版本
⑤ 自动更新衍生树 → 版本号 +1

用户说: "这个功能和原始版本对比有什么不同"
   ↓
① 自动 Diff 分析
② 生成修改摘要:
   ├─ 新增: 翻译功能模块 (3个文件)
   ├─ 修改: 顶部导航栏 (1个文件)
   └─ 删除: 无用示例数据 (2个文件)
```

**商业衍生 → 用户可以发布自己改的项目收费：**

| 衍生等级 | 发布方式 | 收益模式 |
|---------|---------|---------|
| 🆓 免费 | 社区市场 | 声誉/贡献分 |
| 💎 付费 | 付费市场 | 用户定价 |
| 🔒 私有 | 仅自己用 | 不发布 |

---

## 三、工作区高级操作

### 批量操作

```
Ctrl + 点击 → 选中多个节点
框选 → 选中区域内的节点
选中后右键菜单 → 批量操作
├─ [全部启动] [全部停止] [全部重启]
├─ [批量修改端口] [批量设置资源限制]
├─ [合并为新项目] [导出为组合]
└─ [批量删除]
```

### 模板系统

```
保存为模板 →
├─ 名称: "AI 聊天平台"
├─ 包含: Ollama + Open WebUI + Dify
├─ 标签: AI, 聊天, 工作流
├─ 预览图: 画布截图
└─ 发布到: [私有] [团队] [公开]

使用模板 →
├─ 社区模板 → 浏览市场
├─ 一键部署 → 所有配置自动填充
└─ 5分钟 = 完整系统
```

### 资源池/冲突管理

```
----------------------------
资源池状态:
🔴 Ollama 端口: 11434
🟢 WebUI  端口: 8080 (自动分配)
🟢 Dify   端口: 3000
----------------------------
磁盘: 45GB/50GB  ⚡ 剩余不足
建议: [清理缓存] [扩展磁盘]
----------------------------
```

---

## 四、完整数据模型

```python
class ProjectNode:
    """画布上的项目节点"""
    id: str                    # 唯一ID
    name: str                  # 显示名称
    original_name: str         # 原始项目名称 (如果是衍生项目)
    type: str                  # original / fork / compose / template
    source: str                # github / huggingface / local / compose
    repo_url: str              # 原始仓库URL
    category: str              # 分类
    tags: list[str]            # 标签
    tech_stack: list[str]      # 技术栈 (python / node / go / docker...)
    
    # 状态
    status: str                # analyzing / ready / running / stopped / error
    health: str                # healthy / warning / critical
    
    # 运行时
    port: int                  # 映射端口
    container_id: str          # Docker容器ID
    pid: int                   # 进程ID
    cpu: float                 # CPU使用率
    memory: float              # 内存使用
    
    # 配置
    config: dict               # 用户修改的配置
    env_vars: dict             # 环境变量
    resources: dict            # 资源限制 {cpu_max, mem_max}
    routes: list[str]          # Evo路由路径
    auto_start: bool           # 开机自启
    
    # 版本
    version: str               # 当前版本
    base_version: str          # 基于的原始版本 (二次开发)
    fork_from: str             # 衍生自哪个项目ID
    fork_depth: int            # 衍生深度 (0=原始, 1=二次, 2=三次...)
    
    # 衍生
    children: list[str]        # 基于此项目的二次开发列表
    parent: str                # 父项目ID
    
    # 统计
    stars: int                 # ⭐数
    downloads: int             # 下载/安装数
    created_at: datetime
    updated_at: datetime
    
    # 画布位置
    canvas_x: float
    canvas_y: float

class ProjectConnection:
    """画布上的连接线"""
    id: str
    source_id: str             # 源节点
    target_id: str             # 目标节点
    type: str                  # data_flow / api_call / pipeline
    config: dict               # 连接配置 (字段映射等)

class ComposeProject:
    """组合项目"""
    id: str
    name: str
    description: str
    nodes: list[str]           # 包含的子项目ID列表
    connections: list[ProjectConnection]
    unified_port: int          # 统一入口端口
    root_path: str             # 挂载路径
    
    # 衍生能力
    fork_count: int            # 被衍生次数
    latest_fork: str           # 最新衍生项目ID
    template_id: str           # 来源模板

class DevelopmentFork:
    """二次开发衍生"""
    id: str
    name: str                  # 衍生项目名称
    parent_id: str             # 父项目ID
    depth: int                 # 衍生深度
    base_commit: str           # 基于的原始commit
    current_commit: str        # 当前commit
    modified_files: list[str]  # 修改的文件列表
    diff_summary: str          # 修改摘要 (AI生成)
    upstream: str              # 上游原始项目URL
    last_upstream_sync: datetime  # 上次同步上游
    published: bool            # 是否发布到社区
    license: str               # 许可证
    price: float               # 价格 (0=免费)
```

---

## 五、API 设计（完整版）

### 项目管理

```
# 增
POST   /api/v1/hub/projects              # 添加项目 (从发现/URL/本地)
POST   /api/v1/hub/projects/batch        # 批量添加

# 删
DELETE /api/v1/hub/projects/{id}         # 删除项目 (停用/卸载/清理)
DELETE /api/v1/hub/projects/batch        # 批量删除

# 改
PUT    /api/v1/hub/projects/{id}         # 修改项目配置
PATCH  /api/v1/hub/projects/{id}/config  # 修改配置(部分更新)
PATCH  /api/v1/hub/projects/{id}/appearance  # 修改外观
POST   /api/v1/hub/projects/{id}/files   # 修改文件 (code server)
POST   /api/v1/hub/projects/{id}/revert  # 回滚到版本

# 合
POST   /api/v1/hub/composes              # 创建组合
PUT    /api/v1/hub/composes/{id}         # 修改组合
DELETE /api/v1/hub/composes/{id}         # 删除组合
POST   /api/v1/hub/composes/{id}/nodes   # 组合内添加节点
DELETE /api/v1/hub/composes/{id}/nodes/{node_id}  # 组合内删除节点
POST   /api/v1/hub/composes/{id}/connect  # 建立连线
DELETE /api/v1/hub/composes/{id}/connect/{conn_id}  # 删除连线
```

### 二次开发

```
# 创建衍生
POST   /api/v1/hub/projects/{id}/fork
   参数: {name: "MyChat", description: "..."}
   返回: {fork_id, repos_path, editor_url}

# 管理衍生
GET    /api/v1/hub/projects/{id}/forks   # 查看所有衍生版本
GET    /api/v1/hub/forks/{id}/tree       # 查看衍生树
GET    /api/v1/hub/forks/{id}/diff       # 对比差异
POST   /api/v1/hub/forks/{id}/sync-upstream  # 拉取上游更新
POST   /api/v1/hub/forks/{id}/publish   # 发布到社区
POST   /api/v1/hub/forks/{id}/tag       # 打版本标签

# AI辅助开发
POST   /api/v1/hub/ai/suggest-code      # AI建议代码
   参数: {fork_id, request: "加翻译功能"}
   返回: {suggestion: {files: [...], diff: "..."}}
POST   /api/v1/hub/ai/apply-change      # 应用AI修改
   参数: {fork_id, change_id}
```

### 运行时

```
POST   /api/v1/hub/projects/{id}/start
POST   /api/v1/hub/projects/{id}/stop
POST   /api/v1/hub/projects/{id}/restart
GET    /api/v1/hub/projects/{id}/logs   ?tail=100
GET    /api/v1/hub/monitor              # 所有项目实时状态

# 模板
POST   /api/v1/hub/templates
GET    /api/v1/hub/templates
POST   /api/v1/hub/templates/{id}/deploy
```

---

## 六、前端页面组件树（精装版）

```
HubWorkspace (主工作区)
│
├── HubSidebar (左侧面板)
│   ├── SearchBox (搜索框 + 源筛选器)
│   ├── CategoryTree (分类树: AI/Web/数据/工具...)
│   │   └── CategoryItem (分类项 + 计数)
│   ├── QuickFilters (快捷筛选)
│   │   ├── RunningStatus (运行中/已停止/错误)
│   │   ├── ProjectType (原始/衍生/组合)
│   │   └── TechStack (Python/Node/Docker/Go...)
│   └── ResourceMonitor (底部资源监控)
│       ├── CPUGauge (CPU仪表盘)
│       ├── MemoryGauge (内存仪表盘)
│       ├── DiskGauge (磁盘仪表盘)
│       └── PortList (端口占用列表)
│
├── HubCanvas (主画布 — 核心区域)
│   ├── CanvasToolbar (顶部工具栏)
│   │   ├── ZoomControls (缩放 +/- / 适应)
│   │   ├── LayoutButton (自动布局)
│   │   ├── UndoRedo (撤销/重做)
│   │   ├── SaveButton (保存工作区)
│   │   ├── ExportButton (导出为模板)
│   │   └── DeployAllButton (部署全部)
│   │
│   ├── ProjectNode (项目节点 — 画布上每个方块)
│   │   ├── NodeHeader (名称 + 状态指示灯)
│   │   ├── NodeStats (CPU/内存/端口)
│   │   ├── NodeActions (停用/配置/编辑)
│   │   ├── ConnectorPoints (连接点 ●●●)
│   │   │   ├── InputPoint (左侧: 接受连接)
│   │   │   └── OutputPoint (右侧: 发出连接)
│   │   ├── NodeContextMenu (右键菜单)
│   │   │   ├── StartStop (启动/停止)
│   │   │   ├── Configure (配置)
│   │   │   ├── EditCode (编辑源码)
│   │   │   ├── ForkDevelop (二次开发 ← 入口!)
│   │   │   ├── ViewLogs (查看日志)
│   │   │   ├── MergeSelect (合并选中)
│   │   │   └── DeleteMenu (删除级联菜单)
│   │   └── NodeStatusOverlay (拖拽时的状态提示)
│   │
│   ├── ConnectionLine (连接线)
│   │   ├── DrawnLine (绘制中的虚线)
│   │   └── EstablishedLine (已建立连线 + 数据流方向箭头)
│   │
│   ├── ComposeGroup (组合分组框)
│   │   ├── GroupHeader (组合名 + 统一管理控件)
│   │   ├── CollapseButton (折叠/展开)
│   │   └── GroupActions (启动全部/停止全部/导出)
│   │
│   └── CanvasBackground (背景网格/吸附提示)
│
├── NodeDetailPanel (右侧属性面板)
│   ├── ConfigTab (配置)
│   │   ├── GeneralSettings (端口/环境变量/标签/路由)
│   │   ├── AppearanceSettings (名称/图标/颜色/描述)
│   │   └── ResourceSettings (CPU/内存限制)
│   ├── LogsTab (日志)
│   │   ├── LogStream (实时日志流)
│   │   ├── LogSearch (日志搜索)
│   │   └── LogDownload (下载日志)
│   ├── VersionsTab (版本历史)
│   │   ├── VersionList (版本列表 + 回滚按钮)
│   │   ├── DiffViewer (差异对比)
│   │   └── ForkInfo (衍生信息)
│   └── StatsTab (统计)
│       ├── Uptime (运行时长)
│       ├── RequestCount (请求次数)
│       └── ErrorRate (错误率)
│
├── ForkTreeDialog (衍生树弹窗)
│   ├── TreeGraph (家族树可视化)
│   ├── ForkCard (每个衍生版本的卡片)
│   │   ├── VersionInfo (版本号 + 修改摘要)
│   │   ├── StarCount (⭐数)
│   │   └── OpenButton (打开该项目)
│   └── ForkActions (衍生操作: 发布/对比/同步)
│
├── ProjectDiscoverDialog (发现弹窗)
│   ├── TrendingList (热门项目列表)
│   ├── SearchResult (搜索结果)
│   ├── ProjectPreview (项目预览卡片)
│   └── AddToWorkspaceButton (加入工作区按钮)
│
└── TutorialOverlay (首次使用引导)
    ├── StepCard (引导步骤卡片)
    ├── ProgressBar (进度条)
    └── SkipButton (跳过引导)
```

---

## 七、衍生经济模型

### 用户价值阶梯

```
第1级: 使用 (用开源项目)     — 零门槛
第2级: 组合 (拼装项目)       — 零门槛
第3级: 配置 (改设置)         — 零门槛
第4级: 二次开发 (改外观/功能) — 进阶
第5级: 三次开发 (加新功能)    — 开发者
第6级: 独立发布 (自己项目)    — 创造者
第7级: 开源贡献 (回归社区)    — 贡献者
```

### 共赢生态

```
开源作者 ← 获得用户/反馈/贡献
   ↑              ↓
用户 ← 使用/组合/衍生 ← 社区
   ↑                        ↓
Evo平台 ← 提供基础设施 ← 模板市场
```

---

## 八、技术实现要点

### 前端（Vue 3 + VueFlow）

```javascript
// 核心状态管理 (Pinia)
const useHubStore = defineStore('hub', {
  state: () => ({
    projects: {},        // 所有项目 {id: ProjectNode}
    connections: {},     // 所有连线 {id: Connection}
    composes: {},        // 所有组合
    forks: {},           // 所有衍生版本
    canvas: {            // 画布状态
      nodes: [],         // VueFlow节点
      edges: [],         // VueFlow边
      viewport: {x:0, y:0, zoom:1}
    },
    selected: [],        // 选中的节点
    clipboard: null,     // 剪贴板
  }),
  
  actions: {
    async addProject(source) { /* ... */ },
    async deleteProject(id) { /* ... */ },
    async connectProjects(source, target) { /* ... */ },
    async createFork(id) { /* ... */ },
  }
})
```

### 后端（FastAPI + Celery）

```python
# 核心路由
router = APIRouter(prefix="/api/v1/hub")

@router.post("/projects")
async def add_project(req: AddProjectRequest):
    # 1. 解析仓库
    # 2. 分析依赖
    # 3. 检查冲突
    # 4. 分配端口
    # 5. 返回节点配置
    pass

@router.post("/projects/{id}/fork")
async def fork_project(id: str, req: ForkRequest):
    # 1. git clone 到独立目录
    # 2. 创建新的分支
    # 3. 更新衍生树
    # 4. 启动 Code Server
    # 5. 返回编辑器URL
    pass
```

### 运行时管理

```python
class RuntimeManager:
    """项目的进程/容器/Docker管理"""
    
    async def deploy(self, project: ProjectNode):
        if project.has_dockerfile:
            return await self._docker_deploy(project)
        elif project.has_requirements:
            return await self._python_deploy(project)
        elif project.has_package_json:
            return await self._node_deploy(project)
        else:
            return await self._generic_deploy(project)
    
    async def _docker_deploy(self, project):
        # docker-compose up -d
        # 健康检查
        # 端口映射
        pass
```

---

## 九、界面动效规范

| 操作 | 动效 | 时长 |
|------|------|------|
| 节点加入画布 | 从右侧飞入 + 弹性着落 | 0.3s |
| 节点被删除 | 缩小 + 消散粒子 | 0.3s |
| 拖拽连接 | 连线跟随鼠标(弹性弧线) | 实时 |
| 连接建立 | 连线"啪"一声吸附 + 发光 | 0.2s |
| 状态变化 | 节点边框颜色渐变过渡 | 0.5s |
| 组合框选 | 选中框虚影扩缩 | 0.2s |
| 二级开发 | 节点 "嘭" 分裂为两个 (原+衍生) | 0.5s |

---

## 十、开发路线图（细化）

| Phase | 功能 | 工作量 |
|-------|------|--------|
| **P1 — 画布+Pipeline** | VueFlow画布、节点拖拽、连线、运行状态 | 后半 |
| **P2 — 发现+集成** | GitHub API、自动依赖分析、Docker部署 | 4天 |
| **P3 — 修改+管理** | 属性面板、配置编辑、版本历史、日志 | 2天 |
| **P4 — 组合+合并** | 组合分组、统一入口、模板导出 | 2天 |
| **P5 — 二次开发** | Code Server集成、Fork管理、AI辅助 | 3天 |
| **P6 — 社区生态** | 模板市场、衍生树、分享、评分 | 2天 |

---

*设计版本: v0.4 · 2026-06-16*
