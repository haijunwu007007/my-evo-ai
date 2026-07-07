
var _LOCALE=localStorage.getItem('evo_locale')||'zh-CN'
var _TR={
  'zh-CN':{auth_btn:'🚀 进入系统',input_placeholder:'输入你想做的事...',greeting:'你好，{name}！输入你想做的事'},
  'en':{auth_btn:'🚀 Enter',input_placeholder:'What do you want to do...',greeting:'Hello {name}! What can I do?'},
  'ja':{auth_btn:'🚀 入る',input_placeholder:'何をしたいですか...',greeting:'{name}さん！何をしますか？'},
  'ko':{auth_btn:'🚀 입장',input_placeholder:'원하는 것을 입력하세요...',greeting:'{name}님! 무엇을 할까요?'}
}
if(!window.__){function __(k){var t=_TR[_LOCALE]||_TR['zh-CN'];return t[k]||k}}
function setLocale(c){localStorage.setItem('evo_locale',c);window.location.reload()}

var _TOOL_HINTS={"docx_processor":"帮我生成一份文档，主题是：","excel_pro":"帮我创建一个电子表格，包含：","ppt_generator":"帮我生成一份演示文稿，主题是：","pdf_toolkit":"帮我处理这个PDF文件：","code_review":"帮我审查这段代码：","browser_use_task":"帮我用浏览器自动化完成一个任务：","browseract_extract":"帮我用反爬提取这个网页内容：","codemem_query":"帮我查询代码库知识（codebase-memory-mcp）：","gpt_research":"请帮我做一个深度研究：","openhands_generate":"帮我生成一个全栈项目：","letta_message":"记住以下信息到长期记忆：","composio_execute":"使用外部工具执行：","self_evolving_analyze":"帮我分析当前代码库的改进点","moltron_learn":"学习一个新技能：","accomplish_desktop":"执行桌面自动化工作流：","toolbench_discover":"帮我发现可用的外部API：","markitdown_convert":"帮我转换这个文档为Markdown：","scrapegraphai_scrape":"帮我爬取这个网站的数据：","interpreter_execute":"帮我执行这个电脑操作：","s2c_generate":"帮我从截图生成代码：","pra_review":"帮我审查这个PR：","qodo_testgen":"帮我给这个文件生成测试：","aider_edit":"帮我修改这个代码文件：","openclaw_connect":"帮我连接消息平台：","tts_speak":"帮我转换成语音：","chatdev_run":"帮我用多智能体团队完成任务：","autogpt_run":"帮我自主执行这个目标：","agenteval_benchmark":"帮我评测Agent性能：","swe_fix":"帮我分析修复这个Issue：","gptpilot_build":"帮我从需求生成项目：","text2sql_query":"帮我查询数据库：","bolt_generate":"帮我生成Web应用：","openmontage_generate_script":"帮我生成一个视频脚本，主题是：","lida_visualize":"帮我分析数据并生成可视化图表：","paddleocr_image":"帮我识别这张图片中的文字：","paddleocr_pdf":"帮我识别PDF中的文字：","zen_scan":"帮我扫描这个网站的安全漏洞：","shannon_audit":"帮我审计这个目录的代码安全：","legal_review_contract":"帮我审查这份合同：","twenty_create_contact":"帮我在CRM创建一个联系人：","invoice_create":"帮我创建一张发票：","chatwoot_create_ticket":"帮我创建一个客服工单：","postiz_create_post":"帮我在社交媒体发帖：","mautic_send_email":"帮我发送营销邮件：","superset_create_chart":"帮我在Superset创建图表：","dataease_create_dashboard":"帮我创建DataEase仪表盘：","heyform_create_survey":"帮我创建一个问卷调查：","docetl_extract":"帮我提取文档内容：","accord_create_contract":"帮我创建一份协议：","claude_code_generate":"帮我用Claude Code生成代码：","odoo_manage":"帮我管理ERP：","erpclaw_manage":"帮我用AI-ERP管理业务：","coolify_deploy":"帮我在PaaS上部署应用：","rustdesk_connect":"帮我远程连接电脑：","docuseal_sign":"帮我发送电子签名：","homeassistant_control":"帮我控制智能家居设备：","vaultwarden_manage":"帮我管理密码/凭证：","nocodb_manage":"帮我管理数据表格：","appsmith_build":"帮我用低代码构建管理工具：","airbyte_sync":"帮我同步数据管道：","mlflow_track":"帮我追踪AI模型训练：","langfuse_observe":"帮我监控LLM应用：","hoppscotch_test":"帮我测试API：","grist_analyze":"帮我分析电子表格数据：","freshrss_read":"帮我读取RSS资讯：","listmonk_send":"帮我发送邮件：","mermaid_chart":"帮我生成流程图：","nocobase_build":"帮我用低代码构建业务应用：","scriberr_transcribe":"帮我转录音频：","keploy_test":"帮我自动生成API测试：","browseract_extract":"帮我用browseract提取这个网站数据：","codemem_index":"帮我索引这个代码库（codebase-memory-mcp）：","reach_search":"帮我搜索全网信息：","anime_animate":"帮我给这个页面添加动效：","graphify_index":"帮我分析代码库生成知识图谱：","hyper_extract":"帮我从文本提取结构化知识：","kg_query":"帮我查询知识图谱：","headroom_compress":"帮我压缩上下文减少Token消耗：","graphiti_knowledge":"帮我升级知识图谱为时间感知引擎：","mercury_skills":"帮我管理工具权限和Token预算：","aiviz_diagram":"帮我用AI生成专业图表：","opendev_agents":"帮我用并行Agent完成任务：","kilocode_model":"帮我切换AI模型执行：","timesfm_forecast":"帮我做时间序列预测：","eve_learn":"帮我学习 EVE Agent 架构（Vercel filesystem-first）：","openmontage_video":"帮我用 OpenMontage 生成视频：","palmier_mcp":"帮我学习 Palmier Pro MCP 视频编辑："}
// 拓展工具提示（在_TOOL_HINTS声明后追加）
_TOOL_HINTS["loop_library_exec"]="帮我设计一个工作流循环，场景："
_TOOL_HINTS["gstack_dev"]="帮我启动工程团队循环，任务："
_TOOL_HINTS["deer_flow_run"]="帮我创建一个长周期流，名称："
_TOOL_HINTS["cloner_generate"]="帮我用5阶段管道生成网站，规格："
_TOOL_HINTS["odysseus_start"]="帮我创建长运行Agent任务，目标："
_TOOL_HINTS["research_start"]="帮我启动自动研究循环，主题："
var _TOOL_KEYWORDS = [...new Set(["plane_project","openproject_mgmt","cal_schedule","novu_notify","keycloak_auth","meilisearch_search","minio_storage","opentofu_apply","ansible_run","strapi_cms","directus_api","uptime_kuma","oneuptime_monitor","signoz_apm","wazuh_siem","nats_mq","rabbitmq_broker","gitea_git","wikijs_wiki","bookstack_wiki","projectsend_files","odoo_manage","erpclaw_manage","coolify_deploy","rustdesk_connect","docuseal_sign","homeassistant_control","vaultwarden_manage","nocodb_manage","appsmith_build","airbyte_sync","mlflow_track","langfuse_observe","hoppscotch_test","grist_analyze","freshrss_read","listmonk_send","mermaid_chart","nocobase_build","scriberr_transcribe","keploy_test","浏览器","自动化","研究","全栈","生成项目","记忆","composio","外部工具","分析代码","进化","学习技能","桌面","API发现","抓取","爬取","代码审查","测试","编辑代码","语音","多智能体","智能体团队","自主","issue","数据库","部署","k8s","视频","数据可视化","ocr","安全扫描","漏洞","合同","crm","发票","工单","客服","社交媒体","营销","bi","表单","法律","claude"])]
var attachFiles=[];var visionDescs={};
function handleFiles(el){
  for(var i=0;i<el.files.length;i++){
    var f=el.files[i];
    attachFiles.push(f);
    // 自动视觉理解图片
    if(f.type&&f.type.startsWith('image/')){
      var idx=attachFiles.length-1;
      visionDescs[idx]='[图片识别中...]';
      renderAttachBar();
      (function(file,fi){
        var r=new FileReader();
        r.onload=function(e){
          var b64=e.target.result.split(',')[1];
          fetch('/api/v1/vision/understand',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_base64:b64,prompt:'请详细描述这张图片的内容，包括物体、场景、文字、颜色等关键信息'})})
            .then(function(r){return r.json()})
            .then(function(d){
              if(d.success&&d.description){visionDescs[fi]=d.description;renderAttachBar()}
              else{visionDescs[fi]='[图片识别失败]'}
            })
            .catch(function(){visionDescs[fi]='[图片识别失败]'});
        };
        r.readAsDataURL(file);
      })(f,idx);
    }
    // 自动视频理解
    else if(f.type&&f.type.startsWith('video/')){
      var vidx=attachFiles.length-1;
      visionDescs[vidx]='[视频分析中...]';
      renderAttachBar();
      (function(file,fi){
        var fd=new FormData();
        fd.append('file',file);
        fd.append('prompt','请详细描述这个视频的内容，包括画面中的物体、人物、场景、动作等');
        fetch('/api/v1/video-intelligence/analyze',{method:'POST',body:fd})
          .then(function(r){return r.json()})
          .then(function(d){
            if(d.success&&d.description){visionDescs[fi]=d.description.slice(0,200);renderAttachBar()}
            else{visionDescs[fi]='[视频分析失败]'}
          })
          .catch(function(){visionDescs[fi]='[视频分析失败]'});
      })(f,vidx);
    }
  }
  el.value='';
  renderAttachBar();
}
function removeAttach(idx){attachFiles.splice(idx,1);delete visionDescs[idx];renderAttachBar()}
function renderAttachBar(){var bar=document.getElementById('attachBar');if(!bar)return;if(!attachFiles||attachFiles.length===0){bar.innerHTML='';return}var h='';for(var i=0;i<attachFiles.length;i++){var f=attachFiles[i]||{},n=f.name||'file',ico='📄';var desc=visionDescs[i];if(n.match(/\.(png|jpg|jpeg|gif|webp|svg)$/i))ico='🖼️';else if(n.match(/\.(mp4|avi|mov|mkv|webm|flv)$/i))ico='🎬';else if(n.match(/\.(pdf)$/i))ico='📃';else if(n.match(/\.(xlsx|xls|csv)$/i))ico='📊';else if(n.match(/\.(doc|docx)$/i))ico='📝';else if(n.match(/\.(py|js|ts|html|css|java|go|rs)$/i))ico='💻';else if(n.match(/\.(zip|rar|tar|gz)$/i))ico='📦';h+='<span class="attach-chip">'+ico+' '+n.slice(0,12)+(desc?'<span style="font-size:10px;color:#4361ee;margin-left:4px">'+desc.slice(0,18)+'...</span>':'')+'<span class="del" onclick="removeAttach('+i+')">✕</span></span>'}bar.innerHTML=h}
function getAttachInfo(){if(!attachFiles||attachFiles.length===0)return'';var a=[];for(var i=0;i<attachFiles.length;i++){var n=attachFiles[i].name||'file';var d=visionDescs[i];if(d){a.push(n+' ('+d.slice(0,80)+')')}else{a.push(n)}}return'[已上传文件: '+a.join('; ')+']'}
function quickTool(el, name){
  el.classList.add('clicked');setTimeout(function(){el.classList.remove('clicked')},300)
  var inp=document.getElementById('input')
  var hint=(typeof _TOOL_HINTS!=='undefined'&&_TOOL_HINTS[name])||el.textContent.trim()+': '
  inp.value=hint;inp.focus()
}
function toolbarFilter(cat){
  var bodies=document.querySelectorAll('.cat-body');
  var tabs=document.querySelectorAll('.cat-tab');
  tabs.forEach(function(t){t.classList.remove('active')});
  var activeTab=document.getElementById('tbf_'+(cat==='all'?'all':cat));
  if(activeTab)activeTab.classList.add('active');
  bodies.forEach(function(b){
    var bc=b.getAttribute('data-cat')||'';
    if(cat==='all'||bc===cat){
      b.style.display='';
    }else{
      b.style.display='none';
    }
  });
}
function needsTool(msg){var l=msg.toLowerCase();for(var i=0;i<_TOOL_KEYWORDS.length;i++){if(l.indexOf(_TOOL_KEYWORDS[i].toLowerCase())>=0)return true}return false}


var API='/api/v1';var CHAT=[];try{var _tmp=JSON.parse(localStorage.getItem('evo_chat_history')||'[]');if(Array.isArray(_tmp))CHAT=_tmp}catch(e){CHAT=[]};var CTX=[]

async function doRegister(){
  var user=document.getElementById('regUser').value.trim();if(!user||user.length<2){alert('用户名至少2个字符');return}
  var key=document.getElementById('regKey').value.trim();var pass=document.getElementById('regPass').value.trim()
  try{var r=await fetch('/api/v1/user/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});var d=await r.json();if(!d.access_token){await fetch('/api/v1/user/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});var r2=await fetch('/api/v1/user/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});d=await r2.json()}}catch(e){}
  if(d&&d.access_token){localStorage.setItem('evo_token',d.access_token);localStorage.setItem('evo_role',d.role||'user')}
  if(!localStorage.getItem('evo_logged_in')){localStorage.setItem('evo_user',user);localStorage.setItem('evo_logged_in','1');localStorage.setItem('evo_login_ts',Date.now().toString())}
  if(key)localStorage.setItem('evo_api_key',key);document.getElementById('authWrap').classList.remove('active');document.getElementById('appMain').style.display='flex'
  if(typeof checkOnboard==='function')setTimeout(checkOnboard,300)
  document.getElementById('greeting').textContent=__('greeting').replace('{name}',user);restoreHistory();_checkExpert();setTimeout(function(){checkLLM()},1000)
}
function doLogout(){localStorage.removeItem('evo_logged_in');localStorage.removeItem('evo_token');localStorage.removeItem('evo_role');document.getElementById('authWrap').classList.add('active');document.getElementById('appMain').style.display='none'}
function _renderMd(t){return t.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/\n/g,'<br>').replace(/!\[(.*?)\]\(([^)]+)\)/g,function(m,a,s){return '<img src="'+s.replace(/["<>']/g,'')+'" alt="'+a.replace(/["<>']/g,'')+'" style="max-width:100%;border-radius:8px;margin:4px 0">'}).replace(/\[([^\]]+)\]\(([^)]+)\)/g,function(m,t,h){return '<a href="'+h.replace(/["<>'` ]/g,'')+'" target="_blank" rel="noopener">'+t.replace(/["<>']/g,'')+'</a>'})}
function addMsg(t,r){try{CHAT=CHAT||[]}catch(ex){CHAT=[]};var m=document.getElementById('messages');if(!m)return;var d=document.createElement('div');d.className='msg '+r;var l=document.createElement('div');l.className='msg-label';l.textContent=r==='user'?'你':'AUTO-EVO-AI';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=_renderMd(t);d.appendChild(l);d.appendChild(b);m.appendChild(d);m.scrollTop=m.scrollHeight;if(!Array.isArray(CHAT))CHAT=[];CHAT.push({role:r,text:t,time:new Date().toISOString()});if(CHAT.length>100)CHAT=CHAT.slice(-100);try{localStorage.setItem('evo_chat_history',JSON.stringify(CHAT))}catch(ex){};var u=localStorage.getItem('evo_user')||'admin';try{fetch('/api/v1/chat/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,role:r,content:t})})}catch(e){}}
function showLoading(){var m=document.getElementById('messages');var d=document.createElement('div');d.className='msg bot';d.id='loading';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML='<div class="loading-dots"><span></span><span></span><span></span></div>';d.appendChild(b);m.appendChild(d);m.scrollTop=m.scrollHeight}
function hideLoading(){var e=document.getElementById('loading');if(e)e.remove()}
function restoreHistory(){var m=document.getElementById('messages');m.innerHTML='';for(var i=0;i<CHAT.length;i++){var h=CHAT[i];var d=document.createElement('div');d.className='msg '+h.role;var l=document.createElement('div');l.className='msg-label';l.textContent=h.role==='user'?'你':'AUTO-EVO-AI';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=_renderMd(h.text);d.appendChild(l);d.appendChild(b);m.appendChild(d)}m.scrollTop=m.scrollHeight}

var _sendLock=false
async function loadExpert(){quickFill("帮我找一个专家：");document.getElementById("input")?.focus()}

async function processAttachments(){
  if(!attachFiles||attachFiles.length===0) return null;
  var parts=[];
  for(var i=0;i<attachFiles.length;i++){
    var f=attachFiles[i];var n=(f.name||'').toLowerCase();
    var ext=n.split('.').pop();
    // 图片 → OCR
    if(['jpg','jpeg','png','gif','webp','bmp','tiff'].indexOf(ext)>=0){
      try{
        var fd=new FormData();fd.append('file',f,n);
        var r=await fetch('/api/v1/ocr/recognize',{method:'POST',body:fd});
        var d=await r.json();
        if(d.success&&d.text){parts.push('[📄 图片识别: '+n+']\n'+d.text.slice(0,500));
        }else{parts.push('[🖼️ 图片: '+n+']')}
      }catch(e){parts.push('[🖼️ 图片: '+n+']')}
    }
    // 音频 → 转写
    else if(['wav','mp3','flac','ogg','m4a','aac','webm'].indexOf(ext)>=0){
      try{
        var fd2=new FormData();fd2.append('file',f,n);
        var r2=await fetch('/api/v1/audio/transcribe',{method:'POST',body:fd2});
        var d2=await r2.json();
        if(d2.success&&d2.result&&d2.result.text){parts.push('[🎤 音频转写: '+n+']\n'+d2.result.text.slice(0,500));
        }else{parts.push('[🎵 音频: '+n+']')}
      }catch(e){parts.push('[🎵 音频: '+n+']')}
    }
    // 其他文件
    else{parts.push('[📎 '+n+']')}
  }
  return parts.join('\n\n');
}

function send(){
  if(_sendLock)return;_sendLock=true
  try{var input=document.getElementById('input');if(!input)return;_sendLock=false;var text=input.value.trim();var hasAttach=attachFiles&&attachFiles.length>0;if(!text&&!hasAttach)return;input.value='';var ai=null;if(hasAttach){var pa=processAttachments();if(pa&&typeof pa.then==='function'){pa.then(function(r){ai=r;doSend(text,ai)})}else{ai=pa;doSend(text,ai)}}else{doSend(text,null)}
  }catch(e){hideLoading();addMsg('错误: '+e.message,'bot')}_sendLock=false;try{setTimeout(function(){backToVoice()},500)}catch(ex){}
}
async function doSend(text,ai){
  if(!ai)ai=getAttachInfo();var ft=text+(ai?'\n\n📎 '+ai:'');try{CHAT=CHAT||[]}catch(ex){CHAT=[]};addMsg(ft,'user');try{CTX=CTX||[]}catch(ex){CTX=[]};CTX.push({role:'user',content:ft});if(CTX.length>10)CTX=CTX.slice(-10);attachFiles=[];renderAttachBar();showLoading();var ak=localStorage.getItem('evo_api_key')||''
    // 浏览器本地能力：截图/文件/桌面 — 直接在用户浏览器执行
    var _localExec = {
      screenshot: function(){return new Promise(function(resolve){
        if(!navigator.mediaDevices||!navigator.mediaDevices.getDisplayMedia){resolve('截图不可用');return}
        navigator.mediaDevices.getDisplayMedia({video:{mediaSource:'screen'}}).then(function(s){
          var v=document.createElement('video');v.srcObject=s;v.play()
          setTimeout(function(){
            var c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight
            c.getContext('2d').drawImage(v,0,0);s.getTracks().forEach(function(t){t.stop()})
            resolve('截图成功（数据已获取）')
          },500)
        }).catch(function(){resolve('截图被取消')})
      })},
      fileOpen: function(){return new Promise(function(resolve){
        var inp=document.createElement('input');inp.type='file';inp.multiple=true
        inp.onchange=function(){var n=inp.files.length;resolve('已选择 '+n+' 个文件')}
        inp.click()
      })},
      openUrl: function(url){window.open(url,'_blank');return '已打开: '+url},
      clipboard: function(text){navigator.clipboard.writeText(text).then(function(){resolve('已复制到剪贴板')}).catch(function(){resolve('复制失败')})},
      notify: function(msg){if(Notification.permission==='granted'){new Notification('AUTO-EVO-AI',{body:msg})}else{alert(msg)}}
    }
    // ── 浏览器本地直连命令（不经过服务器，直接操作本地浏览器）──
    var lower = text.toLowerCase()
    if(lower.startsWith('打开 ')||lower.startsWith('打开http')||lower.startsWith('打开www')||lower.startsWith('打开https')){
      var url = text.replace(/^打开\s*/,'').trim()
      if(!url.startsWith('http')) url='https://'+url
      _localExec.openUrl(url);addMsg('🌐 '+_localExec.openUrl(url),'bot');hideLoading();return
    }
    if(lower.indexOf('截图')>=0||lower.indexOf('截屏')>=0){
      _localExec.screenshot().then(function(r){addMsg('🖥️ '+r,'bot');hideLoading()})
      return
    }
    if(lower.indexOf('上传')>=0||lower.indexOf('文件')>=0||lower.indexOf('选择文件')>=0){
      _localExec.fileOpen().then(function(r){addMsg('📁 '+r,'bot');hideLoading()})
      return
    }
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


function filterTools(q){
  var tabs=document.querySelectorAll('.cat-strip .cat-tab'),bodies=document.querySelectorAll('.tools-section .cat-body')
  q=q.toLowerCase().trim()
  if(!q){for(var i=0;i<bodies.length;i++){bodies[i].style.display='none'}for(var i=0;i<tabs.length;i++){tabs[i].classList.remove('active')}_activeCat=null;document.getElementById('toolCount').textContent='';return}
  for(var i=0;i<bodies.length;i++){var btns=bodies[i].querySelectorAll('.tool-chip'),matched=0;for(var j=0;j<btns.length;j++){var show=btns[j].textContent.toLowerCase().indexOf(q)>=0;btns[j].style.display=show?'inline-flex':'none';if(show)matched++};bodies[i].style.display=matched>0?'flex':'none';if(tabs[i])tabs[i].classList.toggle('active',matched>0)}
  var total=0,all=document.querySelectorAll('.tool-chip');for(var i=0;i<all.length;i++){if(all[i].style.display!=='none')total++};document.getElementById('toolCount').textContent=total+'/'+all.length
}
(function(){var t=localStorage.getItem('evo_theme');document.getElementById('themeBtn').innerHTML=t==='dark'?'<span class=\"sicon\">🌓</span> 深色':'<span class=\"sicon\">🌙</span> 浅色';if(t==='dark')document.body.classList.add('dark')})()
function toggleTheme(){var b=document.body;b.classList.toggle('dark');var d=b.classList.contains('dark');localStorage.setItem('evo_theme',d?'dark':'light');document.getElementById('themeBtn').innerHTML=d?'<span class="sicon">🌓</span> 深色':'<span class="sicon">🌙</span> 浅色'}

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
  var htmlModel=b.getAttribute('data-model');
  if(htmlModel){
    b.textContent='🧠 '+htmlModel;
    if(s)s.textContent='🧠 模型: '+htmlModel;
  }else{
    b.textContent='⏳ 检测...';
    if(s)s.textContent='⏳ 检测中';
  }
  try{
    var c=new AbortController();setTimeout(function(){c.abort()},8000);
    var r=await fetch('/api/v1/llm/status',{signal:c.signal,cache:'no-store'});
    var d=await r.json();
    if(d&&d.model){
      var name=d.provider?d.provider+'/'+d.model:d.model;
      localStorage.setItem('evo_last_model',name);
      b.textContent='🧠 '+name;
      if(s)s.textContent='🧠 模型: '+name;
    }
  }catch(e){
    if(!htmlModel){b.textContent='🧠 '+htmlModel}
  }
}

document.getElementById('appMain').style.display='flex';try{var _sp=new URLSearchParams(window.location.search);var _en=_sp.get('expert');if(_en){var _ii=document.getElementById('input');if(_ii){_ii.value=_en+'：';_ii.focus()};var _ct=document.getElementById('greeting');if(_ct)_ct.textContent='🎯 已激活专家: '+_en;var _dp=_sp.get('dept')||'';var _sys='你现在是 '+_en+'（'+_dp+'）。你是这个领域的专家，请始终保持这个角色身份回答问题。';try{CTX=CTX||[]}catch(ex){};CTX.push({role:'system',content:_sys});try{CHAT=CHAT||[]}catch(ex){};CHAT=CHAT||[];addMsg('🎯 已激活专家: '+_en+'（'+_dp+'）','bot');var _se=_sp.get('_')||'';window.history.replaceState({},'','/')}else{try{var _ee=JSON.parse(localStorage.getItem('evo_active_expert')||'{}');if(_ee&&_ee.name){var _ii=document.getElementById('input');if(_ii){_ii.value=_ee.name+'：';_ii.focus()}};localStorage.removeItem('evo_active_expert')}catch(_ex){}};if(!_checkExpert()){var gg=document.getElementById('greeting');if(gg)gg.textContent=__('greeting').replace('{name}',localStorage.getItem('evo_user')||'')};restoreHistory();setTimeout(function(){checkLLM()},1000)
function _checkExpert(){try{var e=localStorage.getItem('evo_active_expert');if(!e)return false;var x=JSON.parse(e);if(!x||!x.name){localStorage.removeItem('evo_active_expert');return false};localStorage.removeItem('evo_active_expert');var sys='你现在是 '+x.name+'（'+(x.dept||'')+'）。你是这个领域的专家，请始终保持这个角色身份回答问题。';try{CTX=CTX||[]}catch(ex){CTX=[]};CTX.push({role:'system',content:sys});try{CHAT=CHAT||[]}catch(ex){CHAT=[]};addMsg('🎯 已激活专家: '+x.name+'（'+(x.dept||'')+'）', 'bot');var inp=document.getElementById('input');if(inp){inp.value=x.name+'：';inp.focus();var isEnter=function(e){if(e.key==='Enter')send()};inp.onkeydown=isEnter;alert('_checkExpert: 已设值 '+x.name)};return true}catch(ee){alert('_checkExpert错误: '+ee);return false}
}

