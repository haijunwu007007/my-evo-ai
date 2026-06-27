
var _LOCALE=localStorage.getItem('evo_locale')||'zh-CN'
var _TR={
  'zh-CN':{auth_btn:'🚀 进入系统',input_placeholder:'输入你想做的事...',greeting:'你好，{name}！输入你想做的事'},
  'en':{auth_btn:'🚀 Enter',input_placeholder:'What do you want to do...',greeting:'Hello {name}! What can I do?'},
  'ja':{auth_btn:'🚀 入る',input_placeholder:'何をしたいですか...',greeting:'{name}さん！何をしますか？'},
  'ko':{auth_btn:'🚀 입장',input_placeholder:'원하는 것을 입력하세요...',greeting:'{name}님! 무엇을 할까요?'}
}
function __(k){var t=_TR[_LOCALE]||_TR['zh-CN'];return t[k]||k}
function setLocale(c){localStorage.setItem('evo_locale',c);window.location.reload()}

_TOOL_HINTS["loop_library_exec"]="帮我设计一个工作流循环，场景："
_TOOL_HINTS["gstack_dev"]="帮我启动工程团队循环，任务："
_TOOL_HINTS["deer_flow_run"]="帮我创建一个长周期流，名称："
_TOOL_HINTS["cloner_generate"]="帮我用5阶段管道生成网站，规格："
_TOOL_HINTS["odysseus_start"]="帮我创建长运行Agent任务，目标："
_TOOL_HINTS["research_start"]="帮我启动自动研究循环，主题："
var _TOOL_HINTS={"docx_processor":"帮我生成一份文档，主题是：","excel_pro":"帮我创建一个电子表格，包含：","ppt_generator":"帮我生成一份演示文稿，主题是：","pdf_toolkit":"帮我处理这个PDF文件：","code_review":"帮我审查这段代码：","browser_use_task":"帮我用浏览器自动化完成一个任务：","browseract_extract":"帮我用反爬提取这个网页内容：","codemem_query":"帮我查询代码库知识（codebase-memory-mcp）：","gpt_research":"请帮我做一个深度研究：","openhands_generate":"帮我生成一个全栈项目：","letta_message":"记住以下信息到长期记忆：","composio_execute":"使用外部工具执行：","self_evolving_analyze":"帮我分析当前代码库的改进点","moltron_learn":"学习一个新技能：","accomplish_desktop":"执行桌面自动化工作流：","toolbench_discover":"帮我发现可用的外部API：","markitdown_convert":"帮我转换这个文档为Markdown：","scrapegraphai_scrape":"帮我爬取这个网站的数据：","interpreter_execute":"帮我执行这个电脑操作：","s2c_generate":"帮我从截图生成代码：","pra_review":"帮我审查这个PR：","qodo_testgen":"帮我给这个文件生成测试：","aider_edit":"帮我修改这个代码文件：","openclaw_connect":"帮我连接消息平台：","tts_speak":"帮我转换成语音：","chatdev_run":"帮我用多智能体团队完成任务：","autogpt_run":"帮我自主执行这个目标：","agenteval_benchmark":"帮我评测Agent性能：","swe_fix":"帮我分析修复这个Issue：","gptpilot_build":"帮我从需求生成项目：","text2sql_query":"帮我查询数据库：","bolt_generate":"帮我生成Web应用：","openmontage_generate_script":"帮我生成一个视频脚本，主题是：","lida_visualize":"帮我分析数据并生成可视化图表：","paddleocr_image":"帮我识别这张图片中的文字：","paddleocr_pdf":"帮我识别PDF中的文字：","zen_scan":"帮我扫描这个网站的安全漏洞：","shannon_audit":"帮我审计这个目录的代码安全：","legal_review_contract":"帮我审查这份合同：","twenty_create_contact":"帮我在CRM创建一个联系人：","invoice_create":"帮我创建一张发票：","chatwoot_create_ticket":"帮我创建一个客服工单：","postiz_create_post":"帮我在社交媒体发帖：","mautic_send_email":"帮我发送营销邮件：","superset_create_chart":"帮我在Superset创建图表：","dataease_create_dashboard":"帮我创建DataEase仪表盘：","heyform_create_survey":"帮我创建一个问卷调查：","docetl_extract":"帮我提取文档内容：","accord_create_contract":"帮我创建一份协议：","claude_code_generate":"帮我用Claude Code生成代码：","odoo_manage":"帮我管理ERP：","erpclaw_manage":"帮我用AI-ERP管理业务：","coolify_deploy":"帮我在PaaS上部署应用：","rustdesk_connect":"帮我远程连接电脑：","docuseal_sign":"帮我发送电子签名：","homeassistant_control":"帮我控制智能家居设备：","vaultwarden_manage":"帮我管理密码/凭证：","nocodb_manage":"帮我管理数据表格：","appsmith_build":"帮我用低代码构建管理工具：","airbyte_sync":"帮我同步数据管道：","mlflow_track":"帮我追踪AI模型训练：","langfuse_observe":"帮我监控LLM应用：","hoppscotch_test":"帮我测试API：","grist_analyze":"帮我分析电子表格数据：","freshrss_read":"帮我读取RSS资讯：","listmonk_send":"帮我发送邮件：","mermaid_chart":"帮我生成流程图：","nocobase_build":"帮我用低代码构建业务应用：","scriberr_transcribe":"帮我转录音频：","keploy_test":"帮我自动生成API测试：","browseract_extract":"帮我用browseract提取这个网站数据：","codemem_index":"帮我索引这个代码库（codebase-memory-mcp）：","reach_search":"帮我搜索全网信息：","anime_animate":"帮我给这个页面添加动效：","graphify_index":"帮我分析代码库生成知识图谱：","hyper_extract":"帮我从文本提取结构化知识：","kg_query":"帮我查询知识图谱：","headroom_compress":"帮我压缩上下文减少Token消耗：","graphiti_knowledge":"帮我升级知识图谱为时间感知引擎：","mercury_skills":"帮我管理工具权限和Token预算：","aiviz_diagram":"帮我用AI生成专业图表：","opendev_agents":"帮我用并行Agent完成任务：","kilocode_model":"帮我切换AI模型执行：","timesfm_forecast":"帮我做时间序列预测：","eve_learn":"帮我学习 EVE Agent 架构（Vercel filesystem-first）：","openmontage_video":"帮我用 OpenMontage 生成视频：","palmier_mcp":"帮我学习 Palmier Pro MCP 视频编辑："}
var _TOOL_KEYWORDS = [...new Set(["plane_project","openproject_mgmt","cal_schedule","novu_notify","keycloak_auth","meilisearch_search","minio_storage","opentofu_apply","ansible_run","strapi_cms","directus_api","uptime_kuma","oneuptime_monitor","signoz_apm","wazuh_siem","nats_mq","rabbitmq_broker","gitea_git","wikijs_wiki","bookstack_wiki","projectsend_files","odoo_manage","erpclaw_manage","coolify_deploy","rustdesk_connect","docuseal_sign","homeassistant_control","vaultwarden_manage","nocodb_manage","appsmith_build","airbyte_sync","mlflow_track","langfuse_observe","hoppscotch_test","grist_analyze","freshrss_read","listmonk_send","mermaid_chart","nocobase_build","scriberr_transcribe","keploy_test","浏览器","自动化","研究","全栈","生成项目","记忆","composio","外部工具","分析代码","进化","学习技能","桌面","API发现","抓取","爬取","代码审查","测试","编辑代码","语音","多智能体","智能体团队","自主","issue","数据库","部署","k8s","视频","数据可视化","ocr","安全扫描","漏洞","合同","crm","发票","工单","客服","社交媒体","营销","bi","表单","法律","claude"])]
var attachFiles=[];
function handleFiles(el){for(var i=0;i<el.files.length;i++)attachFiles.push(el.files[i]);renderAttachBar();el.value=''}
function removeAttach(idx){attachFiles.splice(idx,1);renderAttachBar()}
function renderAttachBar(){var bar=document.getElementById('attachBar');if(!bar)return;if(!attachFiles||attachFiles.length===0){bar.innerHTML='';return}var h='';for(var i=0;i<attachFiles.length;i++){var f=attachFiles[i]||{},n=f.name||'file',ico='📄';if(n.match(/\.(png|jpg|jpeg|gif|webp|svg)$/i))ico='🖼️';else if(n.match(/\.(pdf)$/i))ico='📃';else if(n.match(/\.(xlsx|xls|csv)$/i))ico='📊';else if(n.match(/\.(doc|docx)$/i))ico='📝';else if(n.match(/\.(py|js|ts|html|css|java|go|rs)$/i))ico='💻';else if(n.match(/\.(zip|rar|tar|gz)$/i))ico='📦';h+='<span class="attach-chip">'+ico+' '+n.slice(0,18)+'<span class="del" onclick="removeAttach('+i+')">✕</span></span>'}bar.innerHTML=h}
function getAttachInfo(){if(!attachFiles||attachFiles.length===0)return'';var a=[];for(var i=0;i<attachFiles.length;i++)a.push(attachFiles[i].name);return'[已上传文件: '+a.join(', ')+']'}
function quickTool(el, name){
  el.classList.add('clicked');setTimeout(function(){el.classList.remove('clicked')},300)
  var inp=document.getElementById('input')
  inp.value=el.textContent.trim()+': ';inp.focus()
  var isEnter=function(e){if(e.key==='Enter')send()}
  inp.onkeydown=function(){inp.value='';inp.onkeydown=isEnter}
}
function needsTool(msg){var l=msg.toLowerCase();for(var i=0;i<_TOOL_KEYWORDS.length;i++){if(l.indexOf(_TOOL_KEYWORDS[i].toLowerCase())>=0)return true}return false}


var API='/api/v1';var CHAT=[];try{var _tmp=JSON.parse(localStorage.getItem('evo_chat_history')||'[]');if(Array.isArray(_tmp))CHAT=_tmp}catch(e){CHAT=[]};var CTX=[]

async function doRegister(){
  var user=document.getElementById('regUser').value.trim();if(!user||user.length<2){alert('用户名至少2个字符');return}
  var key=document.getElementById('regKey').value.trim();var pass=document.getElementById('regPass').value.trim()
  try{var r=await fetch('/api/v1/user/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});var d=await r.json();if(!d.success&&!d.access_token){await fetch('/api/v1/user/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})})}}catch(e){}
  if(!localStorage.getItem('evo_logged_in')){localStorage.setItem('evo_user',user);localStorage.setItem('evo_logged_in','1');localStorage.setItem('evo_login_ts',Date.now().toString())}
  if(key)localStorage.setItem('evo_api_key',key);document.getElementById('authWrap').classList.add('hidden');document.getElementById('appMain').style.display='flex'
  document.getElementById('greeting').textContent=__('greeting').replace('{name}',user);restoreHistory();_checkExpert();setTimeout(function(){checkLLM()},1000)
}
function doLogout(){localStorage.removeItem('evo_logged_in');document.getElementById('authWrap').classList.remove('hidden');document.getElementById('appMain').style.display='none'}
function _renderMd(t){return t.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/\n/g,'<br>').replace(/!\[(.*?)\]\(([^)]+)\)/g,function(m,a,s){return '<img src="'+s.replace(/["<>']/g,'')+'" alt="'+a.replace(/["<>']/g,'')+'" style="max-width:100%;border-radius:8px;margin:4px 0">'}).replace(/\[([^\]]+)\]\(([^)]+)\)/g,function(m,t,h){return '<a href="'+h.replace(/["<>'` ]/g,'')+'" target="_blank" rel="noopener">'+t.replace(/["<>']/g,'')+'</a>'})}
function addMsg(t,r){try{CHAT=CHAT||[]}catch(ex){CHAT=[]};var m=document.getElementById('messages');if(!m)return;var d=document.createElement('div');d.className='msg '+r;var l=document.createElement('div');l.className='msg-label';l.textContent=r==='user'?'你':'AUTO-EVO-AI';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=_renderMd(t);d.appendChild(l);d.appendChild(b);m.appendChild(d);m.scrollTop=m.scrollHeight;if(!Array.isArray(CHAT))CHAT=[];CHAT.push({role:r,text:t,time:new Date().toISOString()});if(CHAT.length>100)CHAT=CHAT.slice(-100);try{localStorage.setItem('evo_chat_history',JSON.stringify(CHAT))}catch(ex){};var u=localStorage.getItem('evo_user')||'admin';try{fetch('/api/v1/chat/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,role:r,content:t})})}catch(e){}}
function showLoading(){var m=document.getElementById('messages');var d=document.createElement('div');d.className='msg bot';d.id='loading';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML='<div class="loading-dots"><span></span><span></span><span></span></div>';d.appendChild(b);m.appendChild(d);m.scrollTop=m.scrollHeight}
function hideLoading(){var e=document.getElementById('loading');if(e)e.remove()}
function restoreHistory(){var m=document.getElementById('messages');m.innerHTML='';for(var i=0;i<CHAT.length;i++){var h=CHAT[i];var d=document.createElement('div');d.className='msg '+h.role;var l=document.createElement('div');l.className='msg-label';l.textContent=h.role==='user'?'你':'AUTO-EVO-AI';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=_renderMd(h.text);d.appendChild(l);d.appendChild(b);m.appendChild(d)}m.scrollTop=m.scrollHeight}

var _sendLock=false
async function send(){
  if(_sendLock)return;_sendLock=true
  try{var input=document.getElementById('input');if(!input)return;_sendLock=false;var text=input.value.trim();if(!text&&(!attachFiles||attachFiles.length===0))return;input.value='';var ai=getAttachInfo(),ft=text+(ai?'\n\n📎 '+ai:'');try{CHAT=CHAT||[]}catch(ex){CHAT=[]};addMsg(ft,'user');try{CTX=CTX||[]}catch(ex){CTX=[]};CTX.push({role:'user',content:ft});if(CTX.length>10)CTX=CTX.slice(-10);attachFiles=[];renderAttachBar();showLoading();var ak=localStorage.getItem('evo_api_key')||''
    // 先尝试智能任务分解
    var tr=await fetch('/api/v1/task/orchestrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:text})})
    var td=await tr.json()
    if(td.success&&td.workflow_id){
      addMsg('[🎯 系统自动分解任务]\n'+td.steps.map(function(s,i){return '  '+(i+1)+'. '+s}).join('\n')+'\n\n⏳ 正在自动执行...','bot')
    }
    // 走智能对话
    var sr=await fetch('/api/v1/smart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text+'（请参考上面的任务分解逐步执行）',lang:_LOCALE,api_key:ak,provider:'',context:CTX.slice(-6)})})
    if(!sr.ok){hideLoading();addMsg('服务器返回 '+sr.status,'bot');return};var sd=await sr.json();hideLoading()
    if(sd&&sd.success){var rt=sd.result||'(空)'
      if(rt.includes('【模块调用】')||rt.includes('execute_module')||rt.includes('引擎:')){var m=document.getElementById('messages');var d=document.createElement('div');d.className='msg bot';var l=document.createElement('div');l.className='msg-label';l.textContent='AUTO-EVO-AI';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=rt.replace(/</g,'&lt;').replace(/\n/g,'<br>').replace(/!\[(.*?)\]\(([^)]+)\)/g,'<img src="$2" style="max-width:100%;border-radius:8px">').replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank">$1</a>').replace(/【模块调用】/g,'<span style="color:var(--accent);font-weight:bold">【模块调用】</span>').replace(/引擎:/g,'<span style="color:var(--accent2)">引擎:</span>');d.appendChild(l);d.appendChild(b);m.appendChild(d)}else{addMsg(rt,'bot')};if(!CTX)CTX=[];CTX.push({role:'assistant',content:sd.result})
    }else{addMsg('系统: '+(sd&&sd.detail||'未知错误'),'bot')}
  }catch(e){hideLoading();addMsg('错误: '+e.message,'bot')}
  _sendLock=false
  try{setTimeout(function(){backToVoice()},500)}catch(ex){}
}
function clearHistory(){try{CHAT=CHAT||[]}catch(ex){CHAT=[]};if(CHAT.length>0){var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');a.unshift({id:Date.now(),time:new Date().toLocaleString(),messages:[].concat(CHAT)});if(a.length>20)a.length=20;localStorage.setItem('evo_chat_archives',JSON.stringify(a))};CHAT=[];try{CTX=[]}catch(e){};localStorage.removeItem('evo_chat_history');var m=document.getElementById('messages');if(m)m.innerHTML=''}
function showArchives(){var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');if(a.length===0){alert('暂无历史对话');return};var list='';for(var i=0;i<a.length;i++){list+=(i+1)+'. '+a[i].time+' ('+a[i].messages.length+'条)\n'};var idx=prompt('选择要恢复的对话 (输入编号):\n\n'+list);if(idx===null)return;var n=parseInt(idx)-1;if(n>=0&&n<a.length){CHAT=a[n].messages;localStorage.setItem('evo_chat_history',JSON.stringify(CHAT));restoreHistory()}}
function showDashboard(){window.location.href='/dashboard'}
function showEnterprise(){window.location.href='/enterprise.html'}
function showVirtualCompany(){window.location.href='/company.html'}
function openHub(){window.location.href='/hub'}
// 语音 - 双通道：Web Speech API + MediaRecorder降级
var _voicing=false,_voiceWebSpeech=null,_voiceMediaRec=null,_voiceStream=null,_voiceChunks=[];
function switchToText(){
  var el;
  el=document.getElementById('voiceBar');if(el)el.classList.add('hidden');
  el=document.getElementById('textInputRow');if(el)el.style.display='flex';
}
function backToVoice(){
  var el;
  el=document.getElementById('voiceBar');if(el)el.classList.add('hidden');
  el=document.getElementById('textInputRow');if(el)el.style.display='flex';
}
function startVoiceRecord(e){
  if(_voicing)return;_voicing=true
  var b=document.getElementById('voiceMic'),l=document.getElementById('voiceLabel')
  b.classList.add('recording');_voiceChunks=[]
  
  // 检查是否已经拒绝过权限（华为等设备）
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    _fallbackRecord(b,l);return
  }
  
  l.textContent='请说话'
  try{
    navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){
      _voiceStream=s;_voiceReady=true
      var mt=(MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'audio/webm')
      _voiceRec=new MediaRecorder(s,{mimeType:mt})
      _voiceRec.ondataavailable=function(ev){if(ev.data.size>0)_voiceChunks.push(ev.data)}
      _voiceRec.start();l.textContent='松开'
    }).catch(function(){
      // getUserMedia 失败 → 降级到系统原生录音
      _fallbackRecord(b,l)
    })
  }catch(err){
    _fallbackRecord(b,l)
  }
}
// 华为等设备降级方案：弹出系统原生录音界面
var _fallbackInput=null
function _fallbackRecord(b,l){
  b.classList.remove('recording');_voicing=false
  l.textContent='打开录音...'
  if(!_fallbackInput){
    _fallbackInput=document.createElement('input')
    _fallbackInput.type='file';_fallbackInput.accept='audio/*'
    _fallbackInput.setAttribute('capture','user')
    _fallbackInput.style.display='none'
    document.body.appendChild(_fallbackInput)
    _fallbackInput.onchange=function(){
      var f=_fallbackInput.files&&_fallbackInput.files[0]
      _fallbackInput.value=''
      if(!f){l.textContent='🎤语音';return}
      l.textContent='识别中'
      var fd=new FormData();fd.append('file',f,f.name)
      fetch('/api/v1/speech/recognize',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(j){
        var i=document.getElementById('input')
        if(j.success&&j.text&&i){i.value=j.text;l.textContent='🎤语音';send()}
        else{l.textContent='重试';setTimeout(function(){l.textContent='🎤语音'},2000)}
      }).catch(function(){l.textContent='重试';setTimeout(function(){l.textContent='🎤语音'},2000)})
    }
  }
  setTimeout(function(){_fallbackInput.click()},100)
}

function stopVoiceRecord(e){
  if(!_voicing&&!_retrying)return
  var b=document.getElementById('voiceMic'),l=document.getElementById('voiceLabel'),i=document.getElementById('input')
  if(!_voiceReady){
    _retrying=true
    if(!_voicing)_voicing=true
    return setTimeout(function(){_retrying=false;stopVoiceRecord(e)},500)
  }
  _voicing=false;_retrying=false
  b.classList.remove('recording')
  if(!_voiceRec||_voiceRec.state==='inactive'){l.textContent='🎤语音';return}
  _voiceRec.onstop=function(){
    if(_voiceStream){_voiceStream.getTracks().forEach(function(t){t.stop()});_voiceStream=null}
    if(_voiceChunks.length===0){l.textContent='🎤语音';return}
    l.textContent='识别中'
    var fd=new FormData();fd.append('file',new Blob(_voiceChunks,{type:'audio/webm'}),'v.webm');_voiceChunks=[]
    fetch('/api/v1/speech/recognize',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(j){
      if(j.success&&j.text){i.value=j.text;l.textContent='🎤语音';send()}
      else{l.textContent='重试';setTimeout(function(){l.textContent='🎤语音'},2000)}
    }).catch(function(){l.textContent='重试';setTimeout(function(){l.textContent='🎤语音'},2000)})
  }
  try{_voiceRec.stop()}catch(ex){l.textContent='🎤语音'}
}
function cancelVoiceRecord(e){
  if(!_voicing)return;_voicing=false
  var b=document.getElementById('voiceMic'),l=document.getElementById('voiceLabel')
  b.classList.remove('recording');l.textContent='🎤语音'
  if(_voiceRec&&_voiceRec.state!=='inactive'){try{_voiceRec.stop()}catch(ex){}}
  if(_voiceStream){_voiceStream.getTracks().forEach(function(t){t.stop()});_voiceStream=null}
  _voiceChunks=[]
}
function toggleRightPanel(){document.getElementById('rightPanel').classList.toggle('hidden')}
function toggleSidebarMobile(){document.getElementById('sidebar').classList.toggle('open');document.getElementById('sidebarOverlay').classList.toggle('show')}

var _activeCat=null
function toggleCategory(id){
  var el=document.getElementById(id);if(!el)return
  if(_activeCat===id){el.style.display='none';_activeCat=null;_updateActiveTab(null);return}
  if(_activeCat){var p=document.getElementById(_activeCat);if(p)p.style.display='none'}
  el.style.display='flex';_activeCat=id;_updateActiveTab(id)
}
function _updateActiveTab(id){var tabs=document.querySelectorAll('.cat-strip .cat-tab');for(var i=0;i<tabs.length;i++){tabs[i].classList.toggle('active',id&&tabs[i].getAttribute('onclick').indexOf(id)>=0)}}
function filterTools(q){
  var tabs=document.querySelectorAll('.cat-strip .cat-tab'),bodies=document.querySelectorAll('.tools-section .cat-body')
  q=q.toLowerCase().trim()
  if(!q){for(var i=0;i<bodies.length;i++){bodies[i].style.display='none'}for(var i=0;i<tabs.length;i++){tabs[i].classList.remove('active')}_activeCat=null;document.getElementById('toolCount').textContent='';return}
  for(var i=0;i<bodies.length;i++){var btns=bodies[i].querySelectorAll('.tool-chip'),matched=0;for(var j=0;j<btns.length;j++){var show=btns[j].textContent.toLowerCase().indexOf(q)>=0;btns[j].style.display=show?'inline-flex':'none';if(show)matched++};bodies[i].style.display=matched>0?'flex':'none';if(tabs[i])tabs[i].classList.toggle('active',matched>0)}
  var total=0,all=document.querySelectorAll('.tool-chip');for(var i=0;i<all.length;i++){if(all[i].style.display!=='none')total++};document.getElementById('toolCount').textContent=total+'/'+all.length
}
(function(){var t=localStorage.getItem('evo_theme');document.getElementById('themeBtn').innerHTML=t==='dark'?'<span class=\"sicon\">🌓</span> 深色':'<span class=\"sicon\">🌙</span> 浅色';if(t==='dark')document.body.classList.add('dark')})()
function toggleTheme(){var b=document.body;b.classList.toggle('dark');var d=b.classList.contains('dark');localStorage.setItem('evo_theme',d?'dark':'light');document.getElementById('themeBtn').innerHTML=d?'<span class="sicon">🌓</span> 深色':'<span class="sicon">🌙</span> 浅色'}

document.addEventListener('DOMContentLoaded',function(){var s=document.getElementById('catStrip');if(s)s.addEventListener('wheel',function(e){if(e.deltaY!==0){this.scrollLeft+=e.deltaY;e.preventDefault()}},{passive:false})})

// 语音按钮事件绑定（鼠标 + 触摸）
;(function(){
  var btn=document.getElementById('voiceMic')
  if(!btn)return
  btn.addEventListener('mousedown',function(e){e.preventDefault();startVoiceRecord(e)})
  btn.addEventListener('mouseup',function(e){stopVoiceRecord(e)})
  btn.addEventListener('mouseleave',function(e){cancelVoiceRecord(e)})
  btn.addEventListener('touchstart',function(e){e.preventDefault();startVoiceRecord(e)},{passive:false})
  btn.addEventListener('touchend',function(e){stopVoiceRecord(e)})
  btn.addEventListener('touchcancel',function(e){cancelVoiceRecord(e)})
})()

async function checkLLM(){
  var b=document.getElementById('modelBadge');
  var s=document.getElementById('modelStatus');
  var last=localStorage.getItem('evo_last_model')||'';
  b.textContent=last?'🧠 '+last:'⏳ 检测...';
  if(s&&last)s.textContent='🧠 模型: '+last;
  try{
    var r=await fetch('/api/v1/llm/status',{signal:AbortSignal.timeout(8000)});
    var d=await r.json();
    var name='';
    if(d&&d.active&&d.active.length>0){name=d.active[0].name}
    else if(d&&d.providers){
      var a=d.providers.filter(function(p){return p.available});
      if(a.length>0)name=a[0].name;
    }
    if(name){
      localStorage.setItem('evo_last_model',name);
      b.textContent='🧠 '+name;
      if(s)s.textContent='🧠 模型: '+name;
    }else{
      b.textContent=last?'🧠 '+last:'❌ 无模型';
      if(s)s.textContent=last?'🧠 模型: '+last:'❌ 无模型';
    }
  }catch(e){
    b.textContent=last?'🧠 '+last:'❌ 检测失败';
    if(s)s.textContent=last?'🧠 模型: '+last:'❌ 检测失败';
  }
}

var _LOGIN_TTL=86400000;var _loginTs=localStorage.getItem('evo_login_ts')
if(_loginTs&&(Date.now()-parseInt(_loginTs)>_LOGIN_TTL)){localStorage.removeItem('evo_logged_in');localStorage.removeItem('evo_login_ts')}
if(localStorage.getItem('evo_logged_in')){document.getElementById('authWrap').classList.add('hidden');document.getElementById('appMain').style.display='flex';document.getElementById('greeting').textContent=__('greeting').replace('{name}',localStorage.getItem('evo_user')||'');restoreHistory();_checkExpert();setTimeout(function(){checkLLM()},1000)}
function _checkExpert(){try{var e=localStorage.getItem('evo_active_expert');if(!e)return;var x=JSON.parse(e);if(!x||!x.name||!x.dept||Date.now()-x.ts>3600000){localStorage.removeItem('evo_active_expert');return};localStorage.removeItem('evo_active_expert');var sys='你现在是 '+x.name+'（来自 '+x.dept+'）。你是这个领域的专家，请始终保持这个角色身份回答问题。';try{CTX=CTX||[]}catch(e){CTX=[]};CTX.push({role:'system',content:sys});try{CHAT=CHAT||[]}catch(e){CHAT=[]};addMsg('🎯 已激活专家: '+x.name+'（'+x.dept+'）', 'bot');var inp=document.getElementById('input');if(inp){inp.value=x.name+'：';inp.focus();var isEnter=function(e){if(e.key==='Enter')send()};inp.onkeydown=function(){inp.value='';inp.onkeydown=isEnter}}}catch(ee){}
}

