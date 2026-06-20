
// ===== 内联 i18n =====
var _LOCALE = localStorage.getItem('evo_locale') || 'zh-CN'
var _TR = {
  'zh-CN': {title:'⚡ AUTO-EVO-AI', subtitle:'生产力级 AI 自动化编排系统', auth_heading:'🔐 开始使用', auth_user:'用户名', auth_user_placeholder:'你的名字', auth_pass:'密码（可选）', auth_pass_placeholder:'留空即可', auth_key:'API Key（可选）', auth_key_placeholder:'OpenAI / 其他 LLM Key', auth_btn:'🚀 进入系统', greeting:'你好，{name}！输入你想做的事', tab_chat:'💬 对话', tab_dashboard:'📊 仪表盘', tab_business:'🏢 企业管理', input_placeholder:'输入你想做的事...', logout:'🔓 退出', new_chat:'🔄 新对话', archives:'📋 历史'},
  'en': {title:'⚡ AUTO-EVO-AI', subtitle:'Enterprise AI Automation Platform', auth_heading:'🔐 Get Started', auth_user:'Username', auth_user_placeholder:'Your name', auth_pass:'Password (optional)', auth_pass_placeholder:'Leave empty', auth_key:'API Key (optional)', auth_key_placeholder:'OpenAI / other LLM Key', auth_btn:'🚀 Enter', greeting:'Hello {name}! What can I do?', tab_chat:'💬 Chat', tab_dashboard:'📊 Dashboard', tab_business:'🏢 Enterprise', input_placeholder:'What do you want to do...', logout:'🔓 Logout', new_chat:'🔄 New Chat', archives:'📋 History'},
  'ja': {title:'⚡ AUTO-EVO-AI', subtitle:'AI自動化プラットフォーム', auth_heading:'🔐 開始', auth_user:'ユーザー名', auth_user_placeholder:'あなたの名前', auth_pass:'パスワード', auth_pass_placeholder:'空のまま', auth_key:'API Key', auth_key_placeholder:'OpenAI / 他のLLM', auth_btn:'🚀 入る', greeting:'{name}さん！何をしますか？', tab_chat:'💬 チャット', tab_dashboard:'📊 ダッシュボード', tab_business:'🏢 企業管理', input_placeholder:'何をしたいですか...', logout:'🔓 ログアウト', new_chat:'🔄 新規', archives:'📋 履歴'},
  'ko': {title:'⚡ AUTO-EVO-AI', subtitle:'AI 자동화 플랫폼', auth_heading:'🔐 시작', auth_user:'사용자명', auth_user_placeholder:'당신의 이름', auth_pass:'비밀번호', auth_pass_placeholder:'비워두기', auth_key:'API Key', auth_key_placeholder:'OpenAI / 다른 LLM', auth_btn:'🚀 입장', greeting:'{name}님! 무엇을 할까요?', tab_chat:'💬 채팅', tab_dashboard:'📊 대시보드', tab_business:'🏢 기업관리', input_placeholder:'원하는 것을 입력하세요...', logout:'🔓 로그아웃', new_chat:'🔄 새 채팅', archives:'📋 기록'},
  'fr': {title:'⚡ AUTO-EVO-AI', subtitle:'Plateforme IA', auth_heading:'🔐 Commencer', auth_user:'Utilisateur', auth_user_placeholder:'Votre nom', auth_pass:'Mot de passe', auth_pass_placeholder:'Optionnel', auth_key:'API Key', auth_key_placeholder:'OpenAI / autre LLM', auth_btn:'🚀 Entrer', greeting:'Bonjour {name}!', tab_chat:'💬 Discuter', tab_dashboard:'📊 Tableau', tab_business:'🏢 Entreprise', input_placeholder:'Dites...', logout:'🔓 Déconnexion', new_chat:'🔄 Nouveau', archives:'📋 Historique'},
  'es': {title:'⚡ AUTO-EVO-AI', subtitle:'Plataforma IA', auth_heading:'🔐 Comenzar', auth_user:'Usuario', auth_user_placeholder:'Tu nombre', auth_pass:'Contraseña', auth_pass_placeholder:'Opcional', auth_key:'API Key', auth_key_placeholder:'OpenAI / otro LLM', auth_btn:'🚀 Entrar', greeting:'¡Hola {name}!', tab_chat:'💬 Chat', tab_dashboard:'📊 Panel', tab_business:'🏢 Empresa', input_placeholder:'Escribe...', logout:'🔓 Salir', new_chat:'🔄 Nuevo', archives:'📋 Historial'},
  'pt': {title:'⚡ AUTO-EVO-AI', subtitle:'Plataforma IA', auth_heading:'🔐 Começar', auth_user:'Usuário', auth_user_placeholder:'Seu nome', auth_pass:'Senha', auth_pass_placeholder:'Opcional', auth_key:'API Key', auth_key_placeholder:'OpenAI / outro LLM', auth_btn:'🚀 Entrar', greeting:'Olá {name}!', tab_chat:'💬 Conversar', tab_dashboard:'📊 Painel', tab_business:'🏢 Empresa', input_placeholder:'Digite...', logout:'🔓 Sair', new_chat:'🔄 Novo', archives:'📋 Histórico'},
  'ru': {title:'⚡ AUTO-EVO-AI', subtitle:'Платформа ИИ', auth_heading:'🔐 Начать', auth_user:'Пользователь', auth_user_placeholder:'Ваше имя', auth_pass:'Пароль', auth_pass_placeholder:'Опционально', auth_key:'API Key', auth_key_placeholder:'OpenAI / другой LLM', auth_btn:'🚀 Войти', greeting:'Здравствуйте, {name}!', tab_chat:'💬 Чат', tab_dashboard:'📊 Панель', tab_business:'🏢 Управление', input_placeholder:'Введите...', logout:'🔓 Выйти', new_chat:'🔄 Новый', archives:'📋 История'},
  'ar': {title:'⚡ AUTO-EVO-AI', subtitle:'منصة الذكاء', auth_heading:'🔐 ابدأ', auth_user:'المستخدم', auth_user_placeholder:'اسمك', auth_pass:'كلمة المرور', auth_pass_placeholder:'اختياري', auth_key:'مفتاح API', auth_key_placeholder:'OpenAI / LLM آخر', auth_btn:'🚀 دخول', greeting:'{name}! مرحباً', tab_chat:'💬 محادثة', tab_dashboard:'📊 لوحة', tab_business:'🏢 إدارة', input_placeholder:'اكتب...', logout:'🔓 خروج', new_chat:'🔄 جديد', archives:'📋 سجل'}
}
function __(k){var t=_TR[_LOCALE]||_TR['zh-CN']; return t[k]||k}
function setLocale(c){
  localStorage.setItem('evo_locale',c)
  window.location.reload()
}
function toggleCat(el){
  var c = el.classList.toggle('cat-collapsed')
  var sib = el.nextElementSibling
  while(sib && !sib.classList.contains('cat-head')){
    sib.style.display = c ? 'none' : ''
    sib = sib.nextElementSibling
  }
}
function renderLang(){
  var ids=['langBarTop','langBarAuth']
  for(var i=0;i<ids.length;i++){
    var el=document.getElementById(ids[i]); if(!el)continue
    var sel=el.querySelector('select'); if(!sel)continue
    sel.value=_LOCALE
  }
}
function translateUI(){
  var usr=localStorage.getItem('evo_user')||''
  // 标题
  var h1=document.getElementById('mainTitle');if(h1)h1.textContent=__('title')
  var h1a=document.getElementById('authTitle');if(h1a)h1a.textContent=__('title')
  // 副标题
  var sp=document.getElementById('authSub');if(sp)sp.textContent=__('subtitle')
  // 注册标签（用 label 元素的 for 属性定位）
  var lab=document.querySelectorAll('#authCard label')
  if(lab.length>=1)lab[0].textContent=__('auth_user')
  if(lab.length>=2)lab[1].textContent=__('auth_pass')
  if(lab.length>=3)lab[2].textContent=__('auth_key')
  // 注册输入框
  var ru=document.getElementById('regUser');if(ru)ru.placeholder=__('auth_user_placeholder')
  var rp=document.getElementById('regPass');if(rp)rp.placeholder=__('auth_pass_placeholder')
  var rk=document.getElementById('regKey');if(rk)rk.placeholder=__('auth_key_placeholder')
  // 注册按钮
  var rb=document.getElementById('regBtn');if(rb)rb.textContent=__('auth_btn')
  // 问候
  var g=document.getElementById('greeting');if(g)g.textContent=__('greeting').replace('{name}',usr)
  // 退出按钮
  var lb=document.getElementById('logoutBtn');if(lb)lb.textContent=__('logout')
  var nc=document.getElementById('newChatBtn');if(nc)nc.textContent=__('new_chat')
  var ab=document.getElementById('archivesBtn');if(ab)ab.textContent=__('archives')
  // 导航
  var t0=document.getElementById('tabChat');if(t0)t0.textContent=__('tab_chat')
  var t1=document.getElementById('tabDash');if(t1)t1.textContent=__('tab_dashboard')
  var t2=document.getElementById('tabBiz');if(t2)t2.textContent=__('tab_business')
  // 输入框
  var inp=document.getElementById('input');if(inp)inp.placeholder=__('input_placeholder')
  // 语言下拉选中
  renderLang()
}

// ===== 快捷工具 =====
var _TOOL_HINTS = {
  browser_use_task: "帮我用浏览器自动化完成一个任务：",
  browseract_extract: "帮我用反爬提取这个网页内容：",
  codemem_query: "帮我查询代码库知识：",
  gpt_research: "请帮我做一个深度研究：",
  openhands_generate: "帮我生成一个全栈项目：",
  letta_message: "记住以下信息到长期记忆：",
  composio_execute: "使用外部工具执行：",
  self_evolving_analyze: "帮我分析当前代码库的改进点",
  moltron_learn: "学习一个新技能：",
  accomplish_desktop: "执行桌面自动化工作流：",
  toolbench_discover: "帮我发现可用的外部API：",
  markitdown_convert: "帮我转换这个文档为Markdown：",
  scrapegraphai_scrape: "帮我爬取这个网站的数据：",
  interpreter_execute: "帮我执行这个电脑操作：",
  s2c_generate: "帮我从截图生成代码：",
  pra_review: "帮我审查这个PR：",
  qodo_testgen: "帮我给这个文件生成测试：",
  aider_edit: "帮我修改这个代码文件：",
  openclaw_connect: "帮我连接消息平台：",
  openclaw_send: "帮我发送消息：",
  tts_speak: "帮我转换成语音：",
  chatdev_run: "帮我用多智能体团队完成任务：",
  openmanus_run: "帮我运行通用Agent：",
  autogpt_run: "帮我自主执行这个目标：",
  agenteval_benchmark: "帮我评测Agent性能：",
  swe_fix: "帮我分析修复这个Issue：",
  gptpilot_build: "帮我从需求生成项目：",
  text2sql_query: "帮我查询数据库：",
  bolt_generate: "帮我生成Web应用：",
  agentk8s_deploy: "帮我生成K8s部署清单：",
  // 第3轮22个
  openmontage_generate_script: "帮我生成一个视频脚本，主题是：",
  openmontage_search_materials: "帮我搜索视频素材：",
  lida_visualize: "帮我分析数据并生成可视化图表：",
  lida_explore: "帮我探索分析这个数据文件：",
  paddleocr_image: "帮我识别这张图片中的文字：",
  paddleocr_pdf: "帮我识别PDF中的文字：",
  zen_scan: "帮我扫描这个网站的安全漏洞：",
  zen_report: "帮我生成安全报告：",
  shannon_audit: "帮我审计这个目录的代码安全：",
  openant_scan: "帮我扫描这个目标的漏洞：",
  legal_review_contract: "帮我审查这份合同：",
  legal_analyze_compliance: "帮我分析合规性：",
  twenty_create_contact: "帮我在CRM创建一个联系人：",
  twenty_create_deal: "帮我在CRM创建一笔交易：",
  frappe_hr_employee: "帮我查询员工信息：",
  frappe_hr_leave: "帮我提交请假申请：",
  invoice_create: "帮我创建一张发票：",
  invoice_track_expense: "帮我记录一笔费用：",
  chatwoot_create_ticket: "帮我创建一个客服工单：",
  chatwoot_reply_ticket: "帮我回复工单：",
  postiz_create_post: "帮我在社交媒体发帖：",
  mautic_send_email: "帮我发送营销邮件：",
  superset_create_chart: "帮我在Superset创建图表：",
  dataease_create_dashboard: "帮我创建DataEase仪表盘：",
  heyform_create_survey: "帮我创建一个问卷调查：",
  docetl_extract: "帮我提取文档内容：",
  accord_create_contract: "帮我创建一份协议：",
  claude_code_generate: "帮我用Claude Code生成代码：",
  odoo_manage: "帮我管理ERP（会计/库存/采购）：",
  erpclaw_manage: "帮我用AI-ERP管理业务：",
  coolify_deploy: "帮我在PaaS上部署应用：",
  rustdesk_connect: "帮我远程连接电脑：",
  docuseal_sign: "帮我发送电子签名：",
  homeassistant_control: "帮我控制智能家居设备：",
  vaultwarden_manage: "帮我管理密码/凭证：",
  nocodb_manage: "帮我管理数据表格：",
  appsmith_build: "帮我用低代码构建管理工具：",
  airbyte_sync: "帮我同步数据管道：",
  mlflow_track: "帮我追踪AI模型训练：",
  langfuse_observe: "帮我监控LLM应用：",
  hoppscotch_test: "帮我测试API：",
  grist_analyze: "帮我分析电子表格数据：",
  freshrss_read: "帮我读取RSS资讯：",
  listmonk_send: "帮我发送邮件/Newsletter：",
  mermaid_chart: "帮我生成流程图/架构图：",
  nocobase_build: "帮我用低代码构建业务应用：",
  scriberr_transcribe: "帮我转录音频/会议：",
  keploy_test: "帮我自动生成API测试：",
  browseract_extract: "帮我用browseract提取这个网站数据（反爬）：",
  codemem_index: "帮我索引这个代码库并分析：",
  reach_search: "帮我搜索全网信息（推特/小红书/微博）：",
  anime_animate: "帮我给这个页面添加动效："
}
// 需要工具调用（走非流式）的关键词
var _TOOL_KEYWORDS = [...new Set(["plane_project", "openproject_mgmt", "cal_schedule", "novu_notify", "keycloak_auth", "meilisearch_search", "minio_storage", "opentofu_apply", "ansible_run", "strapi_cms", "directus_api", "uptime_kuma", "oneuptime_monitor", "signoz_apm", "wazuh_siem", "nats_mq", "rabbitmq_broker", "gitea_git", "wikijs_wiki", "bookstack_wiki", "projectsend_files", "浏览器","自动化","研究","全栈","生成项目","记忆","composio","外部工具","分析代码","进化","学习技能","桌面","API发现","toolbench","browser","research","openhands","letta","composio","self_evolving","moltron","accomplish","抓取","爬取","操控浏览器","搜索API","发现API",
  // 外部Skill关键词（触发Agent Engine）
  "openclaw","browser-use","crewai","langgraph","mem0","autogen","autogpt","openhands",
  "langchain","dify","flowise","n8n","ragflow","ollama","firecrawl","metagpt",
  "mastra","headroom","odysseus","paseo","claude-mem","context7","goose",
  "ai-hedge-fund","量化交易","股票分析","套利","金融",
  "网络安全","渗透","cyber","hack","网络安全",
  "视频生成","文生视频","图生视频","多模态",
  "odoo_manage", "erpclaw_manage", "coolify_deploy", "rustdesk_connect",
  "docuseal_sign", "homeassistant_control", "vaultwarden_manage", "nocodb_manage",
  "appsmith_build", "airbyte_sync", "mlflow_track", "langfuse_observe",
  "hoppscotch_test", "grist_analyze", "freshrss_read", "listmonk_send",
  "mermaid_chart", "nocobase_build", "scriberr_transcribe", "keploy_test",
  "markdown","转markdown","文档转换","爬虫","爬取数据","计算机","控制电脑","截图","设计转代码","PR","审查","代码审查","测试","单元测试","编辑代码","改代码","telegram","whatsapp","slack","discord","消息平台","语音","tts","播报","朗读","多智能体","智能体团队","自主","autogpt","评测","agent评估","benchmark","issue修复","github issue","生成项目","全栈","数据库","查库","sql查询","查询数据库","deploy","部署","k8s","kubernetes",
  // 第3轮22个
  "视频脚本","视频制作","openmontage","数据可视化","图表","数据分析","ocr","识别图片","识别文字","识别pdf","安全扫描","漏洞扫描","渗透","代码审计","semgrep","漏洞","合同","合规","法律","crm","联系人","交易","hr","员工","请假","发票","开票","费用","工单","客服","ticket","社交媒体","发帖","营销邮件","superset","bi","仪表盘","dataease","问卷调查","heyform","表单","etl","docetl","文档提取","法律协议","合同模板","claude code","代码生成","odoo_manage", "erpclaw_manage", "coolify_deploy", "rustdesk_connect", "docuseal_sign", "homeassistant_control", "vaultwarden_manage", "nocodb_manage", "appsmith_build", "airbyte_sync", "mlflow_track", "langfuse_observe", "hoppscotch_test", "grist_analyze", "freshrss_read", "listmonk_send", "mermaid_chart", "nocobase_build", "scriberr_transcribe", "keploy_test" ])]

function quickTool(name){
  // 先尝试直接调用后端模块 API
  fetch('/api/v1/tool/execute/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success && (d.result || d.doc)){
        var msg = '✅ **' + (d.module||name) + '** 执行成功\n\n' + (d.doc||JSON.stringify(d.result||'ok')).slice(0,500)
        addMsg(msg, 'bot')
        document.getElementById('input').value = ''
      }else{
        var hint = _TOOL_HINTS[name] || ""
        document.getElementById('input').value = hint
        document.getElementById('input').focus()
        setTimeout(function(){ send() }, 2)
      }
    })
    .catch(function(){
      var hint = _TOOL_HINTS[name] || ""
      document.getElementById('input').value = hint
      document.getElementById('input').focus()
      setTimeout(function(){ send() }, 2)
    })
    .catch(function(){
      var hint = _TOOL_HINTS[name] || ""
      document.getElementById('input').value = hint
      document.getElementById('input').focus()
      setTimeout(function(){ send() }, 2)
    })
}

function needsTool(msg){
  var lower = msg.toLowerCase()
  for(var i=0;i<_TOOL_KEYWORDS.length;i++){
    if(lower.indexOf(_TOOL_KEYWORDS[i].toLowerCase())>=0) return true
  }
  return false
}

// ===== 核心功能 =====
var API='/api/v1'
var CHAT=[] // 对话历史
try{var _tmp=JSON.parse(localStorage.getItem('evo_chat_history')||'[]');if(Array.isArray(_tmp))CHAT=_tmp}catch(e){CHAT=[]}
var CTX=[] // 上下文

async function doRegister(){
  var user=document.getElementById('regUser').value.trim()
  if(!user||user.length<2){alert('用户名至少2个字符');return}
  if(user=='admin'){} // 允许admin
  var key=document.getElementById('regKey').value.trim()
  var pass=document.getElementById('regPass').value.trim()
  try{
    var r=await fetch('/api/v1/user/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})})
    var d=await r.json()
    if(!d.success&&!d.access_token){
      var r2=await fetch('/api/v1/user/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})})
      await r2.json()
    }
  }catch(e){console.warn('auth/register fail',e)}
  if(!localStorage.getItem('evo_logged_in')){
    localStorage.setItem('evo_user',user);localStorage.setItem('evo_logged_in','1');localStorage.setItem('evo_login_ts',Date.now().toString())
  }
  if(key)localStorage.setItem('evo_api_key',key)
  document.getElementById('authCard').style.display='none'
  document.getElementById('mainContent').classList.add('show')
  document.getElementById('greeting').textContent=__('greeting').replace('{name}',user)
  // 首次使用欢迎引导
  if(!localStorage.getItem('evo_guide_done')){
    setTimeout(function(){
      var ow=document.createElement('div');ow.id='onboardingOverlay'
      ow.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:99999;display:flex;align-items:center;justify-content:center'
      ow.innerHTML='<div style="background:linear-gradient(135deg,#4361ee,#7209b7);border-radius:16px;padding:32px;max-width:540px;color:#fff;box-shadow:0 20px 60px rgba(0,0,0,0.4);text-align:left"><h2 style="margin:0 0 12px;text-align:center;font-size:20px">🚀 欢迎使用 AUTO-EVO-AI</h2><p style="opacity:0.9;margin:8px 0 16px;line-height:1.8">快速上手：</p><ol style="margin:0 0 16px;padding-left:20px;line-height:2;opacity:0.95"><li>💬 在输入框<strong>打字</strong>，AI自动回复</li><li>🔍 用<strong>搜索框</strong>快速找到94个工具</li><li>🖱️ <strong>点击工具按钮</strong>→自动填充并执行</li><li>🧠 <strong>9个Tab</strong>切换对话/仪表盘/能力中心/蒸馏器/画布/部署器</li><li>⚡ <strong>8大能力</strong>：Codebase理解/自进化/记忆树/权限/多Agent/桌面/角色/多渠道</li><li>🔑 右上角<strong>设置API Key</strong>解锁更多模型</li></ol><p style="opacity:0.8;font-size:13px;margin:0 0 16px;text-align:center">💡 试试搜索"<strong>文档</strong>"或"<strong>部署</strong>"</p><button onclick="document.getElementById(\'onboardingOverlay\').remove();localStorage.setItem(\'evo_guide_done\',\'1\')" style="display:block;margin:0 auto;background:#fff;color:#667eea;border:none;padding:10px 28px;border-radius:8px;font-size:16px;cursor:pointer;font-weight:bold">✓ 知道了，开始使用</button></div>'
      document.body.appendChild(ow)
    }, 500)
  }
  translateUI()
  restoreHistory()
}

function doLogout(){
  localStorage.removeItem('evo_logged_in')
  document.getElementById('authCard').style.display='block'
  document.getElementById('mainContent').classList.remove('show')
}

// 安全渲染Markdown为HTML（XSS防护：剥离事件处理器）
function _renderMd(t){
  return t.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/\n/g,'<br>')
    .replace(/!\[(.*?)\]\(([^)]+)\)/g,function(m,alt,src){
      var s=src.replace(/["<>']/g,'').trim();
      var a=alt.replace(/["<>']/g,'').trim();
      return '<img src="'+s+'" alt="'+a+'" style="max-width:100%;border-radius:8px;margin:4px 0">'
    })
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,function(m,text,href){
      var u=href.replace(/["<>'` ]/g,'').trim();
      var t=text.replace(/["<>']/g,'').trim();
      return '<a href="'+u+'" target="_blank" rel="noopener">'+t+'</a>'
    })
}
function addMsg(t,r){
  var m=document.getElementById('messages')
  var d=document.createElement('div');d.className='msg '+r
  var l=document.createElement('div');l.className='msg-label';l.textContent=r==='user'?'你':'AUTO-EVO-AI'
  var b=document.createElement('div');b.className='msg-bubble'
  b.innerHTML=_renderMd(t)
  d.appendChild(l);d.appendChild(b);m.appendChild(d)
  m.scrollTop=m.scrollHeight
  CHAT.push({role:r,text:t,time:new Date().toISOString()})
  if(CHAT.length>100)CHAT=CHAT.slice(-100)
  localStorage.setItem('evo_chat_history',JSON.stringify(CHAT))
  // 也保存到服务端
  var u=localStorage.getItem('evo_user')||'admin'
  try{fetch('/api/v1/chat/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,role:r,content:t})})}catch(e){console.warn('save fail',e)}
}

function showLoading(){
  var m=document.getElementById('messages')
  var d=document.createElement('div');d.className='msg bot';d.id='loading'
  var b=document.createElement('div');b.className='msg-bubble'
  b.innerHTML='<div class="loading-dots"><span></span><span></span><span></span></div>'
  d.appendChild(b);m.appendChild(d);m.scrollTop=m.scrollHeight
}
function hideLoading(){var e=document.getElementById('loading');if(e)e.remove()}

function restoreHistory(){
  var m=document.getElementById('messages');m.innerHTML=''
  for(var i=0;i<CHAT.length;i++){
    var h=CHAT[i]
    var d=document.createElement('div');d.className='msg '+h.role
    var l=document.createElement('div');l.className='msg-label';l.textContent=h.role==='user'?'你':'AUTO-EVO-AI'
    var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=_renderMd(h.text)
    d.appendChild(l);d.appendChild(b);m.appendChild(d)
  }
  m.scrollTop=m.scrollHeight
}

async function send(){
  try{
    var input=document.getElementById('input')
    var text=input.value.trim()
    if(!text)return
    input.value=''
    addMsg(text,'user')
    CTX.push({role:'user',content:text})
    if(CTX.length>10)CTX=CTX.slice(-10)
    showLoading()
    var ak=localStorage.getItem('evo_api_key')||''
    var useTools=needsTool(text)

    // 超时30s的fetch包装
    async function tFetch(url,opts,ms=30000){
      var c=new AbortController()
      var t=setTimeout(function(){c.abort()},ms)
      try{
        var r=await fetch(url,Object.assign({},opts,{signal:c.signal}))
        clearTimeout(t)
        return r
      }catch(e){
        clearTimeout(t)
        if(e.name==='AbortError') throw new Error('⏱️ LLM 响应超时，正在降级处理...')
        throw e
      }
    }

    // 非流式请求：直接走 smart（稳定可靠）
    var sr=await fetch('/api/v1/smart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,lang:_LOCALE,api_key:ak,provider:'',context:CTX.slice(-6)})})
    if(!sr.ok){hideLoading();addMsg('服务器返回 '+sr.status,'bot');document.getElementById('sendBtn').disabled=false;return}
    var sd=await sr.json()
    hideLoading()
    if(sd&&sd.success){
      var resultText=sd.result||'(空)'
      if(resultText.includes('【模块调用】')||resultText.includes('execute_module')||resultText.includes('引擎:')){
        var m=document.getElementById('messages')
        var d=document.createElement('div');d.className='msg bot'
        var l=document.createElement('div');l.className='msg-label';l.textContent='AUTO-EVO-AI'
        var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=resultText.replace(/</g,'&lt;').replace(/\n/g,'<br>').replace(/!\[(.*?)\]\(([^)]+)\)/g,'<img src="$2" style="max-width:100%;border-radius:8px">').replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank">$1</a>').replace(/【模块调用】/g,'<span style="color:#4361ee;font-weight:bold">【模块调用】</span>').replace(/引擎:/g,'<span style="color:#7209b7">引擎:</span>')
        d.appendChild(l);d.appendChild(b);m.appendChild(d)
      }else{
        addMsg(resultText,'bot')
      }
      CTX.push({role:'assistant',content:sd.result})
    }else{
      addMsg('系统: '+(sd&&sd.detail||'未知错误'),'bot')
    }
  }catch(e){hideLoading();addMsg('错误: '+e.message,'bot')}
  document.getElementById('sendBtn').disabled=false;input.focus()
}

function clearHistory(){
  if(CHAT.length>0){
    var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]')
    a.unshift({id:Date.now(),time:new Date().toLocaleString(),messages:[].concat(CHAT)})
    if(a.length>20)a.length=20
    localStorage.setItem('evo_chat_archives',JSON.stringify(a))
  }
  CHAT=[];CTX=[];localStorage.removeItem('evo_chat_history');document.getElementById('messages').innerHTML=''
}

function showArchives(){
  var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]')
  if(a.length===0){alert('暂无历史对话');return}
  var list=''
  for(var i=0;i<a.length;i++){list+=(i+1)+'. '+a[i].time+' ('+a[i].messages.length+'条)\n'}
  var idx=prompt('选择要恢复的对话 (输入编号):\n\n'+list)
  if(idx===null)return
  var n=parseInt(idx)-1
  if(n>=0&&n<a.length){CHAT=a[n].messages;localStorage.setItem('evo_chat_history',JSON.stringify(CHAT));restoreHistory()}
}

function showDashboard(){window.location.href='/dashboard'}
function showEnterprise(){window.location.href='/enterprise.html'}
function showVirtualCompany(){window.location.href='/company.html'}
function openHub(){window.location.href='/hub'}

function startVoice(){
  var SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition
  if(!SpeechRecognition){alert('您的浏览器不支持语音输入');return}
  var r=new SpeechRecognition();r.lang=_LOCALE;r.continuous=false;r.interimResults=false
  r.onresult=function(e){document.getElementById('input').value=e.results[0][0].transcript;send()}
  r.start()
}

// ===== 工具搜索 =====
function filterTools(q){
  var btns=document.querySelectorAll('.quick-actions .qa'), cnt=0
  q=q.toLowerCase().trim()
  for(var i=0;i<btns.length;i++){
    var t=btns[i].textContent.toLowerCase()
    if(!q||t.indexOf(q)>=0){btns[i].style.display='inline-flex';cnt++}else{btns[i].style.display='none'}
  }
  document.getElementById('toolCount').textContent=cnt+'/'+btns.length
}

// ===== 全局主题切换 =====
(function(){var t=localStorage.getItem('evo_theme');if(t==='light'){document.body.classList.add('light');document.getElementById('themeBtn').textContent='🌙'}else{document.getElementById('themeBtn').textContent='🌓'}})()
function toggleTheme(){var b=document.body;b.classList.toggle('light');var l=b.classList.contains('light');localStorage.setItem('evo_theme',l?'light':'dark');document.getElementById('themeBtn').textContent=l?'🌙':'🌓'}
// ===== LLM状态检测 =====
async function checkLLM(){
  var badge=document.getElementById('modelBadge')
  badge.textContent='⏳ 检测...'
  try{
    var r=await fetch('/api/v1/llm/status',{signal:AbortSignal.timeout(5000)})
    var d=await r.json()
    if(d&&d.active&&d.active.length>0){
      var m=d.active[0]
      badge.textContent='🧠 '+m.name
      badge.title='当前模型: '+m.name+' (优先级:'+m.priority+')'
    }else if(d&&d.providers){
      var avail=d.providers.filter(function(p){return p.available})
      if(avail.length>0){badge.textContent='🧠 '+avail[0].name
        badge.title='可用: '+avail.map(function(p){return p.name}).join(', ')}else{badge.textContent='❌ 无模型'
        badge.title='所有模型均不可用，请配置 API Key'}
    }else{badge.textContent='❌ 无模型'}
  }catch(e){badge.textContent='❌ 检测失败';badge.title='LLM服务未响应'}
}

// ===== 初始化 =====
var _LOGIN_TTL=86400000 // 24小时会话过期（毫秒）
var _loginTs=localStorage.getItem('evo_login_ts')
if(_loginTs&&(Date.now()-parseInt(_loginTs)>_LOGIN_TTL)){
  localStorage.removeItem('evo_logged_in')
  localStorage.removeItem('evo_login_ts')
}
if(localStorage.getItem('evo_logged_in')){
  document.getElementById('authCard').style.display='none'
  document.getElementById('mainContent').classList.add('show')
  document.getElementById('greeting').textContent=__('greeting').replace('{name}',localStorage.getItem('evo_user')||'')
  translateUI()
  restoreHistory()
  // 延迟检测LLM状态
  setTimeout(function(){checkLLM()},1000)
}
translateUI()
