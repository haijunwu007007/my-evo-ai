# AUTO-EVO-AI 行业解决方案

> 20 个行业 × 真实业务场景 × 即用方案

---

## 🏭 1. 制造业 — 进销存 + 生产管理

| 痛点 | 方案 | 工具 |
|------|------|------|
| 库存不准、采购混乱 | **ERPNext 进销存** | ERPNext |
| 生产进度不透明 | 生产工单 + 工序跟踪 | ERPNext |
| 供应商管理混乱 | 供应商门户 + 采购审批 | ERPNext |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d erpnext-db erpnext
```

**使用流程：**
1. 打开 ERPNext → 设置公司信息
2. 创建物料清单（BOM）
3. 录入供应商 → 创建采购订单
4. 收货 → 入库 → 生产领料
5. 销售订单 → 出库 → 开票

---

## 🏪 2. 零售业 — 电商 + POS + 会员

| 痛点 | 方案 | 工具 |
|------|------|------|
| 没有线上店铺 | **Medusa 电商平台** | Medusa |
| 客户管理混乱 | 客户管理 + 订单追踪 | Medusa + Twenty CRM |
| 财务对账难 | 发票自动生成 | Invoice Ninja |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d medusa-db medusa-redis medusa
```

---

## 🏦 3. 金融业 — 报表 + 合规 + 数据看板

| 痛点 | 方案 | 工具 |
|------|------|------|
| 数据分散看不到全局 | **BI 数据看板** | Metabase |
| 合规审计难 | 审计日志 + 报表 | OpenProject |
| 合同管理乱 | 电子签署 + 归档 | Documenso + Paperless |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d metabase metabase-db
```

---

## 🏥 4. 医疗业 — 电子病历 + 诊所管理

| 痛点 | 方案 | 工具 |
|------|------|------|
| 病历纸质化 | **电子病历系统** | OpenEMR |
| 预约管理乱 | 预约排班系统 | OpenEMR |
| 处方管理麻烦 | 电子处方 | OpenEMR |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d openemr-db openemr
```

---

## 🎓 5. 教育业 — LMS 在线学习 + 课程管理

| 痛点 | 方案 | 工具 |
|------|------|------|
| 课程没有线上化 | **在线学习平台** | Open edX |
| 学员管理难 | 学员管理 + 成绩 | Open edX |
| 内容单一 | 文档协作 + 媒体 | Docmost + Jellyfin |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d openedx
```

---

## 👥 6. 人力资源 — 招聘 + 考勤 + 工资

| 痛点 | 方案 | 工具 |
|------|------|------|
| 招聘流程乱 | **HR 全流程** | Frappe HR |
| 考勤统计麻烦 | 打卡 → 考勤报表 | Frappe HR |
| 工资计算复杂 | 薪资核算 + 个税 | Frappe HR |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d frappe-hr-db frappe-hr
```

---

## 🏢 7. 企业服务 — CRM + 客服 + 合同

| 痛点 | 方案 | 工具 |
|------|------|------|
| 客户信息散落 | **统一 CRM** | Twenty CRM |
| 客服响应慢 | 多渠道客服 | Chatwoot + osTicket |
| 合同签署麻烦 | 电子签 | Documenso |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d twenty-db twenty chatwoot-db chatwoot
```

---

## 💻 8. IT 科技公司 — 代码 + 资产 + 监控

| 痛点 | 方案 | 工具 |
|------|------|------|
| 代码托管在公有云 | **私有 Git 服务** | Gitea |
| IT 资产不知谁在用 | 资产追踪 | Snipe-IT |
| 服务挂了不知道 | 监控告警 | Grafana + Prometheus |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d gitea snipe-it-db snipe-it grafana
```

---

## ⚖️ 9. 法务/律所 — 合同 + 文档 + 签名

| 痛点 | 方案 | 工具 |
|------|------|------|
| 合同堆积 | **文档归档 + OCR** | Paperless-ngx |
| 签署流程长 | 电子签名 | Documenso |
| 团队协作差 | 协作文档 | Docmost |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d paperless-db paperless-redis paperless documenso-db documenso
```

---

## 🎬 10. 媒体/影视 — 影音 + 照片 + 白板

| 痛点 | 方案 | 工具 |
|------|------|------|
| 视频文件分散 | **私人影音库** | Jellyfin |
| 照片管理乱 | 照片备份 + AI 识别 | Immich |
| 画图/方案沟通 | 在线白板 | Excalidraw |

**启动：**
```bash
docker compose -f docker-compose.tools.yml up -d jellyfin immich immich-db excalidraw
```

---

## 🛒 11. 电商运营 — 店铺 + 客服 + 邮件

| 痛点 | 方案 | 工具 |
|------|------|------|
| 多店铺管理难 | 电商中台 | Medusa |
| 售后客服乱 | 统一客服 | Chatwoot |
| 营销邮件不会发 | 自动化邮件 | n8n |

---

## 📦 12. 物流/仓储 — WMS + 订单 + 调度

| 痛点 | 方案 | 工具 |
|------|------|------|
| 库存不准 | **仓储管理系统** | ERPNext WMS |
| 配送调度乱 | 运输管理 | ERPNext |
| 签收回单难 | 电子签名 | Documenso |

---

## 🏗️ 13. 建筑/工程 — 项目 + 文档 + 图纸

| 痛点 | 方案 | 工具 |
|------|------|------|
| 项目进度不透明 | 项目管理 | Focalboard |
| 图纸版本混乱 | 文件管理 | Nextcloud |
| 验收签字麻烦 | 电子签署 | Documenso |

---

## 🍔 14. 餐饮/酒店 — POS + 预订 + 会员

| 痛点 | 方案 | 工具 |
|------|------|------|
| 点餐效率低 | 在线点餐 | Medusa |
| 预订管理乱 | 预订系统 | ERPNext |
| 会员营销难 | 会员管理 | Twenty CRM |

---

## 🚚 15. 运输/物流 — 车队 + 路由 + 签收

| 痛点 | 方案 | 工具 |
|------|------|------|
| 车辆管理乱 | 车队管理 | ERPNext |
| 路由规划差 | 路由调度 | n8n (自动化) |
| 签收无凭证 | 电子签名 | Documenso |

---

## 🧪 16. 实验室/研发 — 记录 + 数据 + 协作

| 痛点 | 方案 | 工具 |
|------|------|------|
| 实验记录纸质化 | 协作文档 | Docmost |
| 数据分散 | 数据看板 | Metabase |
| 团队协作差 | 团队通讯 | Mattermost |

---

## 🏫 17. 培训/咨询 — 课程 + 客户 + 交付

| 痛点 | 方案 | 工具 |
|------|------|------|
| 课程管理乱 | 学习平台 | Open edX |
| 客户跟踪差 | CRM | Twenty CRM |
| 交付物管理 | 文档协作 | Docmost |

---

## 🔧 18. 维修/售后 — 工单 + 派工 + 备件

| 痛点 | 方案 | 工具 |
|------|------|------|
| 报修流程乱 | 工单系统 | osTicket |
| 派工调度难 | 维修调度 | ERPNext |
| 备件库存乱 | 备件管理 | Snipe-IT |

---

## 📱 19. 互联网/软件 — DevOps + 监控 + 协作

| 痛点 | 方案 | 工具 |
|------|------|------|
| CI/CD 没有 | 代码 + 流水线 | Gitea |
| 服务无人盯 | 监控告警 | Grafana |
| 文档混乱 | Wiki | Docmost |

---

## 🏠 20. 物业管理 — 报修 + 收费 + 公告

| 痛点 | 方案 | 工具 |
|------|------|------|
| 报修处理慢 | 工单系统 | osTicket |
| 收费对账难 | 账单管理 | Invoice Ninja |
| 通知靠吼 | 公告推送 | Mattermost |

---

## 🚀 一键启动行业方案

```bash
# 启动对应行业的全部 Docker 服务
docker compose -f docker-compose.tools.yml up -d <服务列表>
```

或使用启动脚本：
```bash
python deploy.py --industry 制造业
```

---

> 每个行业方案都已集成到侧边栏 → 外部工具页面。
> 启动对应容器后，打开工具即可开始使用。

---

### 行业 21-40（新增）

| # | 行业 | 核心工具 | 解决什么问题 |
|---|------|---------|-------------|
| 21 | 🌾 **农业** | ERPNext + Metabase | 种植计划/农资/产量分析 |
| 22 | 🏗️ **建筑业** | ERPNext + Focalboard | 项目预算/材料/进度 |
| 23 | 🚚 **运输业** | ERPNext + Snipe-IT | 车队管理/调度/维修 |
| 24 | 🛡️ **保险业** | Twenty CRM + Paperless | 客户/保单/理赔 |
| 25 | 📡 **电信** | Grafana + osTicket | 网络监控/客服/计费 |
| 26 | 🚗 **汽车** | ERPNext + Snipe-IT | 配件/维修/库存 |
| 27 | ✈️ **航空** | Grafana + Metabase | 安全/调度/维护 |
| 28 | 🚢 **航运** | ERPNext + Paperless | 船舶/货运/报关 |
| 29 | ⛏️ **矿业** | ERPNext + Grafana | 开采/设备/安全 |
| 30 | 🍔 **食品饮料** | ERPNext + Paperless | 配方/质检/追溯 |
| 31 | 🏀 **体育** | Twenty CRM + Immich | 会员/赛事/训练 |
| 32 | 🎭 **娱乐** | Jellyfin + Immich | 内容/版权/票务 |
| 33 | 📺 **广告** | Twenty CRM + Excalidraw | 客户/创意/投放 |
| 34 | 📖 **出版** | Calibre-Web + Docmost | 稿件/编审/发行 |
| 35 | 🔬 **科研** | Docmost + Metabase | 实验/数据/论文 |
| 36 | 🌿 **环保** | Grafana + Miniflux | 监测/报告/政策 |
| 37 | 🚔 **安保** | Vaultwarden + osTicket | 门禁/巡逻/出勤 |
| 38 | 💅 **美容** | Twenty CRM + Invoice Ninja | 会员/预约/消费 |
| 39 | ⛪ **社区** | Twenty CRM + Paperless | 成员/捐赠/活动 |
| 40 | 🌍 **跨境电商** | Medusa + Invoice Ninja | 跨境/报关/多币种 |
