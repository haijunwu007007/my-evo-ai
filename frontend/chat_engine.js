
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
var _TEAMMATES = []; // 从API加载AI同事列表
// ── 异步加载队友列表 ──
async function loadTeammates(){
  try{
    var r=await fetch('/api/v1/teammates/list');
    var d=await r.json();
    if(d.success&&d.teammates&&d.teammates.length){_TEAMMATES=d.teammates;localStorage.setItem('evo_teammates',JSON.stringify(d.teammates))}
  }catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}}
  // 兜底：从localStorage加载
  try{var _tm=JSON.parse(localStorage.getItem('evo_teammates')||'[]');if(Array.isArray(_tm)&&_tm.length>0)_TEAMMATES=_tm}catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}}
}
setTimeout(loadTeammates,500);
function suggestInput(val){
  var el=document.getElementById('inputSuggest');
  if(!el)return;
  if(!val||val.length<2){el.classList.remove('show');el.innerHTML='';return}
  // @召唤：同时显示AI同事和工具
  if(val.indexOf('@')>=0){
    var at=val.split('@').pop().toLowerCase().trim()
    var items=[]
    // AI同事
    if(_TEAMMATES&&_TEAMMATES.length){
      _TEAMMATES.forEach(function(t){
        if(t.name.toLowerCase().indexOf(at)>=0)items.push({type:'teammate',name:t.name,label:t.description||'AI同事'})
      })
    }
    // 工具
    if(typeof _TOOL_HINTS!=='undefined'&&_TOOL_HINTS){
      for(var k in _TOOL_HINTS){
        if(k.toLowerCase().indexOf(at)>=0||_TOOL_HINTS[k].toLowerCase().indexOf(at)>=0)items.push({type:'tool',name:k,label:_TOOL_HINTS[k]})
      }
    }
    if(items.length===0){el.classList.remove('show');el.innerHTML='';return}
    var html=items.slice(0,8).map(function(it,i){
      var active=i===0?'active':''
      if(it.type==='teammate') return '<div class="si '+active+'" onclick="summonTeammate(\''+it.name+'\')">🤖 <b>'+it.name+'</b><span class="sibadge">AI同事</span></div>'
      return '<div class="si '+active+'" onclick="fillTool(\''+it.name+'\')">🔧 '+it.label.slice(0,40)+'<span class="sibadge">'+it.name+'</span></div>'
    }).join('');
    el.innerHTML=html;el.classList.add('show');return
  }
  var matches=[];
  for(var k in _TOOL_HINTS){if(_TOOL_HINTS[k].toLowerCase().indexOf(val.toLowerCase())>=0)matches.push({key:k,label:_TOOL_HINTS[k]})}
  if(matches.length===0){el.classList.remove('show');el.innerHTML='';return}
  var html=matches.slice(0,5).map(function(m,i){return '<div class="si '+(i===0?'active':'')+'" onclick="fillTool(\''+m.key+'\')">'+m.label.slice(0,40)+'... <span class="sibadge">'+m.key+'</span></div>'}).join('');
  el.innerHTML=html;
  el.classList.add('show');
}
function fillTool(key){
  var t=_TOOL_HINTS[key]||''
  document.getElementById('input').value=t
  document.getElementById('input').focus()
  document.getElementById('inputSuggest').classList.remove('show')
}
function summonTeammate(name){
  document.getElementById('input').value='@'+name+' '
  document.getElementById('input').focus()
  document.getElementById('inputSuggest').classList.remove('show')
  // 查找TEAMMATES数据重新激活
  for(var i=0;i<_TEAMMATES.length;i++){
    if(_TEAMMATES[i].name===name){
      var sys='你现在是 '+name+'（AI同事）。'+_TEAMMATES[i].prompt+' 请始终保持这个角色身份回答问题。'
      localStorage.setItem('evo_active_expert',JSON.stringify({name:name,dept:'AI同事',system:sys}))
      // 立即生效
      try{CTX=CTX||[]}catch(ex){CTX=[]};CTX.push({role:'system',content:sys})
      addMsg('🤖 已召唤AI同事: '+name,'bot')
      break
    }
  }
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


var API='/api/v1';var CHAT=[];try{var _tmp=JSON.parse(localStorage.getItem('evo_chat_history')||'[]');if(Array.isArray(_tmp))CHAT=_tmp}catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}CHAT=[]};var CTX=[]

async function doRegister(){
  var user=document.getElementById('regUser').value.trim();if(!user||user.length<2){alert('用户名至少2个字符');return}
  var email=document.getElementById('regEmail')?.value.trim()||''
  var phone=document.getElementById('regPhone')?.value.trim()||''
  var key=document.getElementById('regKey').value.trim();var pass=document.getElementById('regPass').value.trim()
  if(!pass||pass.length<3){alert('密码至少3个字符');return}
  try{
    var r=await fetch('/api/v1/user/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});var d=await r.json()
    if(!d.access_token){
      var rr=await fetch('/api/v1/user/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass,email:email,phone:phone})});var dd=await rr.json()
      if(!dd.success){alert(dd.error||'注册失败');return}
      var r2=await fetch('/api/v1/user/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:user,password:pass})});d=await r2.json()
    }
  }catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}alert('网络错误: '+e.message);return}
  if(d&&d.access_token){localStorage.setItem('evo_token',d.access_token);localStorage.setItem('evo_role',d.role||'user')}
  if(!localStorage.getItem('evo_logged_in')){localStorage.setItem('evo_user',user);localStorage.setItem('evo_logged_in','1');localStorage.setItem('evo_login_ts',Date.now().toString())}
  if(key)localStorage.setItem('evo_api_key',key);document.getElementById('authWrap').classList.remove('active');document.getElementById('appMain').style.display='flex'
  if(typeof checkOnboard==='function')setTimeout(checkOnboard,300)
  document.getElementById('greeting').textContent=__('greeting').replace('{name}',user);restoreHistory();_checkExpert();setTimeout(function(){checkLLM()},1000)
}
function demoMode(){
  document.getElementById('regUser').value='demo';
  document.getElementById('regPass').value='demo123';
  document.getElementById('regEmail').value='demo@evo.ai';
  document.getElementById('regPhone').value='';
  document.getElementById('regKey').value='';
  doRegister();
}
function doLogout(){localStorage.removeItem('evo_logged_in');localStorage.removeItem('evo_token');localStorage.removeItem('evo_role');document.getElementById('authWrap').classList.add('active');document.getElementById('appMain').style.display='none'}
function showPasswordReset(){
  var input=prompt('请输入注册时填写的邮箱或手机号，我们将发送重置码')
  if(!input||input.trim().length<3)return
  fetch('/api/v1/user/password-reset/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:input,phone:''})})
    .then(function(r){return r.json()}).then(function(d){
      if(!d.success){alert(d.error||'请求失败');return}
      var code=prompt('重置码已生成。请输入重置码：')
      if(!code)return
      var np=prompt('请输入新密码（至少3位）：')
      if(!np||np.length<3){alert('密码至少3位');return}
      fetch('/api/v1/user/password-reset/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:code.trim(),new_password:np})})
        .then(function(r){return r.json()}).then(function(d2){
          if(d2.success){alert('密码已重置，请用新密码登录')}
          else{alert(d2.error||'重置失败')}
        })
    }).catch(function(e){alert('网络错误: '+e.message)})
}
function _renderMd(t,r){
  var html=t.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/\n/g,'<br>').replace(/!\[(.*?)\]\(([^)]+)\)/g,function(m,a,s){return '<img src="'+s.replace(/["<>']/g,'')+'" alt="'+a.replace(/["<>']/g,'')+'" style="max-width:100%;border-radius:8px;margin:4px 0">'}).replace(/\[([^\]]+)\]\(([^)]+)\)/g,function(m,t,h){return '<a href="'+h.replace(/["<>'` ]/g,'')+'" target="_blank" rel="noopener">'+t.replace(/["<>']/g,'')+'</a>'})
  if(r==='bot'&&t.length>20){html+='<span class="copy-btn" onclick="navigator.clipboard.writeText(\''+t.replace(/['"\\]/g,'').slice(0,2000)+'\');this.textContent=\"已复制\"" style="display:inline-block;font-size:10px;color:var(--text3);cursor:pointer;margin-left:6px">📋</span>'}
  return html
}
function friendlyError(msg){var m=msg||'';if(m.indexOf('502')>=0)return'服务暂时不可用，请稍后重试';if(m.indexOf('timeout')>=0||m.indexOf('timed out')>=0)return'请求超时，可能是网络或服务器负载较高';if(m.indexOf('500')>=0)return'服务器内部错误，已记录日志';if(m.indexOf('404')>=0)return'资源不存在';if(m.indexOf('Failed to fetch')>=0||m.indexOf('NetworkError')>=0)return'网络连接失败，请检查网络';return m.slice(0,120)}
// ── 搜索缓存 ──
var _searchCacheTTL=3600000;
function _cachedSearch(url,cb){var now=Date.now();try{var raw=localStorage.getItem('evo_cache_'+btoa(url));if(raw){var cached=JSON.parse(raw);if(now-cached.ts<_searchCacheTTL){cb(cached.data);return}}}catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}}fetch(url).then(function(r){if(r.status!==200)return r.text().then(function(t){cb(null)});return r.json().then(function(d){try{localStorage.setItem('evo_cache_'+btoa(url),JSON.stringify({data:d,ts:now}))}catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}}cb(d)})}).catch(function(){cb(null)})}
function addMsg(t,r){try{CHAT=CHAT||[]}catch(ex){CHAT=[]};var m=document.getElementById('messages');if(!m)return;var d=document.createElement('div');d.className='msg '+r;var l=document.createElement('div');l.className='msg-label';l.textContent=r==='user'?'你':'AUTO-EVO-AI';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=_renderMd(t,r);d.appendChild(l);d.appendChild(b);m.appendChild(d);m.scrollTop=m.scrollHeight;if(!Array.isArray(CHAT))CHAT=[];CHAT.push({role:r,text:t,time:new Date().toISOString()});if(CHAT.length>100)CHAT=CHAT.slice(-100);try{localStorage.setItem('evo_chat_history',JSON.stringify(CHAT))}catch(ex){};var u=localStorage.getItem('evo_user')||'admin';try{fetch('/api/v1/chat/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,role:r,content:t})})}catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}}}
function showLoading(msg){msg=msg||'思考中';var m=document.getElementById('messages');var d=document.createElement('div');d.className='msg bot';d.id='loading';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML='<div class="thinking-status" id="thinkingStatus"><span id="thinkingIcon">🤔</span><span id="thinkingText">'+msg+'</span><span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span></div>';d.appendChild(b);m.appendChild(d);m.scrollTop=m.scrollHeight}
function updateThinking(icon,msg){var s=document.getElementById('thinkingStatus');if(!s){// 不存在则创建
showLoading(msg);s=document.getElementById('thinkingStatus')};if(s){var ic=document.getElementById('thinkingIcon');if(ic)ic.textContent=icon;var tx=document.getElementById('thinkingText');if(tx)tx.textContent=msg}}
function hideLoading(){var e=document.getElementById('loading');if(e)e.remove()}
function restoreHistory(){var m=document.getElementById('messages');m.innerHTML='';for(var i=0;i<CHAT.length;i++){var h=CHAT[i];var d=document.createElement('div');d.className='msg '+h.role;var l=document.createElement('div');l.className='msg-label';l.textContent=h.role==='user'?'你':'AUTO-EVO-AI';var b=document.createElement('div');b.className='msg-bubble';b.innerHTML=_renderMd(h.text);d.appendChild(l);d.appendChild(b);m.appendChild(d)}m.scrollTop=m.scrollHeight}

// ── 状态机: IDLE / TALKING ──
var _chatState = 'idle' // 'idle' | 'talking' | 'queued'
function _setState(s){_chatState=s}
function _isTalking(){return _chatState==='talking'}
var _MSG_QUEUE = [] // 消息队列
var _THINK_TIMER = null // 10秒超时计时器

function _startThinkTimer(){
  if(_THINK_TIMER)clearTimeout(_THINK_TIMER)
  _THINK_TIMER=setTimeout(function(){
    var tx=document.getElementById('thinkingText')
    if(tx)tx.textContent='请等待，LLM响应较慢...'
    var ic=document.getElementById('thinkingIcon')
    if(ic)ic.textContent='⏳'
  },10000)
}
function _clearThinkTimer(){
  if(_THINK_TIMER){clearTimeout(_THINK_TIMER);_THINK_TIMER=null}
}

// 处理消息队列
function _processQueue(){
  if(_MSG_QUEUE.length===0){var _q=document.getElementById('queueCount');if(_q)_q.remove();return}
  if(_chatState==='talking'||_chatState==='queued')return
  var next=_MSG_QUEUE.shift()
  var _q=document.getElementById('queueCount')
  if(_q)_q.textContent=_MSG_QUEUE.length>0?'📌 队列中（'+_MSG_QUEUE.length+'条待处理）':''
  var inp=document.getElementById('input')
  if(inp){inp.value=next;send()}
}

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
      }catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}parts.push('[🖼️ 图片: '+n+']')}
    }
    // 音频 → 转写
    else if(['wav','mp3','flac','ogg','m4a','aac','webm'].indexOf(ext)>=0){
      try{
        var fd2=new FormData();fd2.append('file',f,n);
        var r2=await fetch('/api/v1/audio/transcribe',{method:'POST',body:fd2});
        var d2=await r2.json();
        if(d2.success&&d2.result&&d2.result.text){parts.push('[🎤 音频转写: '+n+']\n'+d2.result.text.slice(0,500));
        }else{parts.push('[🎵 音频: '+n+']')}
      }catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}parts.push('[🎵 音频: '+n+']')}
    }
    // 其他文件
    else{parts.push('[📎 '+n+']')}
  }
  return parts.join('\n\n');
}


// ── 粘贴文件 ──
document.addEventListener('paste',function(e){
  var files=e.clipboardData.files
  if(files.length){attachFiles=attachFiles||[];for(var i=0;i<files.length;i++)attachFiles.push(files[i]);renderAttachBar()}
})

async function send(){
  try{var input=document.getElementById('input');if(!input)return;var text=input.value.trim();var hasAttach=attachFiles&&attachFiles.length>0;if(!text&&!hasAttach)return;
  if(_isTalking()){_MSG_QUEUE.push(text);input.value='';var _q=document.getElementById('queueCount');if(!_q){_q=document.createElement('div');_q.id='queueCount';_q.style.cssText='text-align:center;font-size:11px;color:var(--text3);padding:2px;background:var(--bg);border-radius:4px;margin:2px 0';document.getElementById('messages').appendChild(_q)};_q.textContent='📌 已加入队列（'+_MSG_QUEUE.length+'条待处理）';return}
  _setState('talking');input.value='';var ai=null;
  if(hasAttach){var pa=processAttachments();if(pa&&typeof pa.then==='function'){pa.then(function(r){ai=r;doSend(text,ai)})}else{ai=pa;doSend(text,ai)}}else{doSend(text,null)}
  }catch(e){_setState('idle');addMsg('❌ 出错了: '+e.message,'bot')}try{setTimeout(function(){backToVoice()},500)}catch(ex){}
}
async function doSend(text,ai){try{
  if(!ai)ai=getAttachInfo();var ft=text+(ai?'\n\n📎 '+ai:'');try{CHAT=CHAT||[]}catch(ex){CHAT=[]};addMsg(ft,'user');try{CTX=CTX||[]}catch(ex){CTX=[]};CTX.push({role:'user',content:ft});if(CTX.length>10)CTX=CTX.slice(-10);attachFiles=[];renderAttachBar()
  
  // ── 创建单条助手消息（内含思考状态）──
  var msgEl=document.createElement('div');msgEl.className='msg bot';msgEl.id='loading'
  var label=document.createElement('div');label.className='msg-label';label.textContent='AUTO-EVO-AI'
  var bubble=document.createElement('div');bubble.className='msg-bubble'
  bubble.innerHTML='<div class="thinking-status" id="thinkingStatus"><span id="thinkingIcon">🧠</span><span id="thinkingText">接收指令</span><span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span></div>'
  msgEl.appendChild(label);msgEl.appendChild(bubble)
  var m=document.getElementById('messages');m.appendChild(msgEl);m.scrollTop=m.scrollHeight

  var ak=localStorage.getItem('evo_api_key')||''
  // ── 浏览器本地直连命令 ──
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
  var lower = text.toLowerCase()
  if(lower.startsWith('打开 ')||lower.startsWith('打开http')||lower.startsWith('打开www')||lower.startsWith('打开https')){
    var url = text.replace(/^打开\s*/,'').trim()
    if(!url.startsWith('http')) url='https://'+url
    _localExec.openUrl(url);bubble.innerHTML='🌐 '+_localExec.openUrl(url);    msgEl.id='';_clearThinkTimer();_setState('idle');_processQueue();return
  }
  if(lower.indexOf('截图')>=0||lower.indexOf('截屏')>=0){
    _localExec.screenshot().then(function(r){bubble.innerHTML='🖥️ '+r;msgEl.id='';_clearThinkTimer();_setState('idle');_processQueue()})
    return
  }
  if(lower.indexOf('上传')>=0||lower.indexOf('文件')>=0||lower.indexOf('选择文件')>=0){
    _localExec.fileOpen().then(function(r){bubble.innerHTML='📁 '+r;msgEl.id='';_clearThinkTimer();_setState('idle');_processQueue()})
    return
  }
  // 先尝试智能任务分解
  // 判断意图类型
  var _createIntents=['生成','创建','制作','写一个','做一个','开发','画图','设计','html','代码','报告','合同','方案','excel','表格','ppt','演示']
  var _isCreate=_createIntents.some(function(k){return text.includes(k)})
  if(_isCreate){updateThinking('✍️','正在生成内容')}else{updateThinking('🧠','分析任务')}
  _startThinkTimer()
  var tr=await fetch('/api/v1/task/orchestrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:text})})
  var td=await tr.json()
  if(td.success&&td.workflow_id){
    var steps=td.steps||[]
    bubble.innerHTML='<div class="thinking-status"><span>📋</span><span>任务拆解完成</span><span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span></div>'
    // 逐个显示步骤状态
    for(var _si=0;_si<steps.length;_si++){
      updateThinking('⏳','步骤'+(1+_si)+': '+steps[_si].slice(0,20)+'...')
      bubble.innerHTML+='<br><span style="color:var(--text3)">  ⏳ 步骤'+(1+_si)+': '+_renderMd(steps[_si])+'</span>'
      m.scrollTop=m.scrollHeight
    }
    updateThinking('⚡','正在自动执行...')
  }
  // 尝试流式SSE（生成类不走SSE，直接POST）
  if(!_isCreate) try{
    updateThinking('🔍','搜索信息')
    var sr_stream=await fetch('/api/v1/smart/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,lang:_LOCALE,api_key:ak,provider:'',context:CTX.slice(-6)})})
    if(sr_stream.ok&&sr_stream.headers.get('content-type','').includes('text/event-stream')){
      var reader=sr_stream.body.getReader();var decoder=new TextDecoder();var buf='';var _firstChunk=true
      while(true){
        var {done,value}=await reader.read()
        if(done){msgEl.id='';break}
        buf+=decoder.decode(value,{stream:true})
        var lines=buf.split('\n');buf=lines.pop()||''
        for(var line of lines){
          if(line.startsWith('data: ')){
            try{
              var d=JSON.parse(line.slice(6))
              if(d.thinking){
                var ts=bubble.querySelector('#thinkingStatus')
                if(ts){var ic=bubble.querySelector('#thinkingIcon');if(ic)ic.textContent=d.icon||'🧠';var tx=bubble.querySelector('#thinkingText');if(tx)tx.textContent=d.thinking}
                continue}
              if(d.done){break}
              // 第一条非thinking数据 → 移除thinking元素，保留bubble
              if(_firstChunk){_firstChunk=false;var _ts=document.getElementById('thinkingStatus');if(_ts&&_ts.parentNode)_ts.parentNode.removeChild(_ts)}
              var txt=(bubble.textContent||'')+d.chunk
              bubble.innerHTML=_renderMd(txt)
              m.scrollTop=m.scrollHeight
            }catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}}
          }
        }
      }
      try{CTX=CTX||[];CTX.push({role:'assistant',content:bubble.textContent||''})}catch(ex){}
      _clearThinkTimer();_setState('idle');_processQueue();return
    }
  }catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}/*stream fallback*/}
  // 非流式 — 不创建新元素，直接更新loading泡的内容
  updateThinking('🤔','正在思考')
  var sr=await fetch('/api/v1/smart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text+'（请参考上面的任务分解逐步执行）',lang:_LOCALE,api_key:ak,provider:'',context:CTX.slice(-6)})})
  if(!sr.ok){
    if(sr.status===429) bubble.innerHTML='⚠️ 请求太频繁，请稍后再试'
    else bubble.innerHTML='❌ 请求失败 ('+sr.status+') 请稍后重试'
    msgEl.id='';_clearThinkTimer();_setState('idle');_processQueue();return
  }
  var sd=await sr.json();msgEl.id=''
  if(sd&&sd.success){
    if(sd.redirect){
      bubble.innerHTML=sd.result||'📌 正在跳转...'
      setTimeout(function(){window.location.href=sd.redirect},800)
    } else {
      var rt=sd.result||'(空)'
      bubble.innerHTML=_renderMd(rt)
    }
    if(!CTX)CTX=[];CTX.push({role:'assistant',content:sd.result})
  } else {
    bubble.innerHTML='❌ 系统返回错误，请重试'
  }
  _clearThinkTimer();_setState('idle');_processQueue()
}catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}_clearThinkTimer();var lb=document.getElementById('loading');if(lb)lb.innerHTML='❌ 出错了: '+e.message;else addMsg('❌ 出错了: '+e.message,'bot');_setState('idle');_processQueue()}
_sendLock=false
try{setTimeout(function(){backToVoice()},500)}catch(ex){}
}
function clearHistory(){if(typeof Evo!=='undefined'&&Evo.confirm){Evo.confirm('确认开启新对话？当前对话将存入历史',function(ok){if(ok)_doClear()})}else{if(!confirm('确认开启新对话？当前对话将存入历史'))return;_doClear()};function _doClear(){try{CHAT=CHAT||[]}catch(ex){CHAT=[]};if(CHAT.length>0){var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');a.unshift({id:Date.now(),time:new Date().toLocaleString(),messages:[].concat(CHAT)});if(a.length>20)a.length=20;localStorage.setItem('evo_chat_archives',JSON.stringify(a))};CHAT=[];try{CTX=[]}catch(e){/* ignore */};localStorage.removeItem('evo_chat_history');var m=document.getElementById('messages');if(m)m.innerHTML=''}}
function showArchives(){var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');if(a.length===0){alert('暂无历史对话');return};var list='';for(var i=0;i<a.length;i++){list+=(i+1)+'. '+a[i].time+' ('+a[i].messages.length+'条)\n'};var idx=prompt('选择要恢复的对话 (输入编号):\n\n'+list);if(idx===null)return;var n=parseInt(idx)-1;if(n>=0&&n<a.length){CHAT=a[n].messages;localStorage.setItem('evo_chat_history',JSON.stringify(CHAT));restoreHistory()}}
function showHistory(){
  var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');
  var rp=document.getElementById('rightPanel');
  if(rp.classList.contains('hidden')){
    rp.classList.remove('hidden');
    var parent=rp.parentElement;
    parent.classList.add('right-panel-visible');
  }
  var overlay=document.getElementById('historyOverlay');
  if(!overlay){
    overlay=document.createElement('div');
    overlay.id='historyOverlay';
    overlay.style.cssText='position:fixed;top:0;right:0;width:320px;max-width:85vw;height:100vh;z-index:999;background:var(--card);border-left:1px solid var(--border);overflow-y:auto;padding:12px;box-shadow:-4px 0 20px rgba(0,0,0,.15)';
    var sh=document.createElement('input');
    sh.placeholder='🔍 搜索历史...';
    sh.style.cssText='width:100%;padding:8px 10px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;margin-bottom:8px';
    sh.oninput=function(){
      var q=this.value.toLowerCase().trim()
      document.querySelectorAll('.hi').forEach(function(el){
        el.style.display=q&&el.textContent.toLowerCase().indexOf(q)<0?'none':'block'
      })
    };
    overlay.insertBefore(sh,overlay.firstChild);
    overlay.onclick=function(e){if(e.target===overlay)closeHistoryOverlay()};

    document.body.appendChild(overlay);
  }
  var h='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px"><h4 style="margin:0">📋 对话历史</h4><span onclick="closeHistoryOverlay()" style="cursor:pointer;font-size:18px;padding:4px 8px;border-radius:4px">✕</span></div>';
  if(a.length===0){h+='<div style="padding:20px;text-align:center;color:var(--text3)">暂无历史对话</div>'}
  for(var i=0;i<a.length;i++){
    var n=a[i].name||('对话 '+(i+1));
    var cnt=a[i].messages?Math.ceil(a[i].messages.length/2):0;
    h+='<div onclick="restoreArchive('+i+')" style="display:flex;align-items:center;gap:8px;padding:10px 8px;border-radius:8px;cursor:pointer;margin-bottom:4px;background:var(--bg);transition:background .15s" onmouseover="this.style.background=\'var(--sidebar-hover)\'" onmouseout="this.style.background=\'var(--bg)\'"><span>💬</span><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px">'+n.slice(0,20)+'</span><span style="font-size:12px;color:var(--text3)">'+cnt+'条</span><span onclick="event.stopPropagation();renameArchive('+i+')" style="cursor:pointer;font-size:14px">✏️</span><span onclick="event.stopPropagation();deleteArchive('+i+')" style="cursor:pointer;font-size:14px;color:#e74c3c">🗑️</span></div>';
  }
  overlay.innerHTML=h;
  overlay.style.display='block';
  document.getElementById('historyBtn').textContent='📜 历史';
}
function closeHistoryOverlay(){
  var overlay=document.getElementById('historyOverlay');
  if(overlay)overlay.style.display='none';
}
function restoreArchive(idx){
  var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');
  if(!a[idx])return;
  CHAT=a[idx].messages||[];
  localStorage.setItem('evo_chat_history',JSON.stringify(CHAT));
  restoreHistory();
  document.getElementById('historyBtn').textContent='📜 历史';
  closeRightPanel();
  closeHistoryOverlay();
}
function renameArchive(idx){
  var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');
  if(!a[idx])return;
  var n=prompt('重命名对话:',a[idx].name||'');
  if(n&&n.trim()){a[idx].name=n.trim();localStorage.setItem('evo_chat_archives',JSON.stringify(a));showHistory()}
}
function deleteArchive(idx){
  if(!confirm('确认删除此对话？'))return;
  var a=JSON.parse(localStorage.getItem('evo_chat_archives')||'[]');
  a.splice(idx,1);
  localStorage.setItem('evo_chat_archives',JSON.stringify(a));
  showHistory();
}
function showEnterprise(){window.location.href='/enterprise.html'}
function showVirtualCompany(){window.location.href='/company.html'}
function openHub(){window.location.href='/hub'}
// 语音 - 双通道：Web Speech API + MediaRecorder降级
var _voicing=false,_voiceWebSpeech=null,_voiceMediaRec=null,_voiceStream=null,_voiceChunks=[];
function switchToText(){
  var el;
  el=document.getElementById('voiceBar');if(el){el.classList.add('hidden');el.style.display=''}
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
function toggleRightPanel(){var p=document.getElementById('rightPanel');var parent=p.parentElement;p.classList.toggle('hidden');parent.classList.toggle('right-panel-visible')}
function closeRightPanel(){var p=document.getElementById('rightPanel');var parent=p.parentElement;if(!p.classList.contains('hidden')){p.classList.add('hidden');parent.classList.remove('right-panel-visible')}}
function toggleSidebarMobile(){document.getElementById('sidebar').classList.toggle('open');document.getElementById('sidebarOverlay').classList.toggle('show')}


function filterTools(q){
  var tabs=document.querySelectorAll('.cat-strip .cat-tab'),bodies=document.querySelectorAll('.tools-section .cat-body')
  q=q.toLowerCase().trim()
  if(!q){for(var i=0;i<bodies.length;i++){bodies[i].style.display='none'}for(var i=0;i<tabs.length;i++){tabs[i].classList.remove('active')}_activeCat=null;document.getElementById('toolCount').textContent='';return}
  for(var i=0;i<bodies.length;i++){var btns=bodies[i].querySelectorAll('.tool-chip'),matched=0;for(var j=0;j<btns.length;j++){var show=btns[j].textContent.toLowerCase().indexOf(q)>=0;btns[j].style.display=show?'inline-flex':'none';if(show)matched++};bodies[i].style.display=matched>0?'flex':'none';if(tabs[i])tabs[i].classList.toggle('active',matched>0)}
  var total=0,all=document.querySelectorAll('.tool-chip');for(var i=0;i<all.length;i++){if(all[i].style.display!=='none')total++};document.getElementById('toolCount').textContent=total+'/'+all.length
}
// ── 亮/暗主题切换 ──
function toggleTheme(){
  document.body.classList.toggle('dark')
  var isDark=document.body.classList.contains('dark')
  localStorage.setItem('evo_theme',isDark?'dark':'light')
  var btn=document.getElementById('themeBtn')
  if(btn)btn.innerHTML=isDark?'<span class="sicon">☀️</span> 深色':'<span class="sicon">🌙</span> 浅色'
  if(t.vars){
    for(var k in t.vars){document.documentElement.style.setProperty(k,t.vars[k])}
  }
}
// 恢复主题（亮/暗）
try{if(localStorage.getItem('evo_theme')==='dark'){document.body.classList.add('dark');var btn=document.getElementById('themeBtn');if(btn)btn.innerHTML='<span class="sicon">☀️</span> 深色'}}catch(ex){}

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
  }catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}
    if(!htmlModel){b.textContent='🧠 '+htmlModel}
  }
}

document.getElementById('appMain').style.display='flex';{var _sp=new URLSearchParams(window.location.search);var _en=_sp.get('expert');if(_en){var _ii=document.getElementById('input');if(_ii){_ii.value=_en+'：';_ii.focus()};var _ct=document.getElementById('greeting');if(_ct)_ct.textContent='🎯 已激活专家: '+_en;var _dp=_sp.get('dept')||'';var _sys='你现在是 '+_en+'（'+_dp+'）。你是这个领域的专家，请始终保持这个角色身份回答问题。';try{CTX=CTX||[]}catch(ex){};CTX.push({role:'system',content:_sys});try{CHAT=CHAT||[]}catch(ex){};CHAT=CHAT||[];addMsg('🎯 已激活专家: '+_en+'（'+_dp+'）','bot');var _se=_sp.get('_')||'';window.history.replaceState({},'','/')}else{try{var _ee=JSON.parse(localStorage.getItem('evo_active_expert')||'{}');if(_ee&&_ee.name){var _ii=document.getElementById('input');if(_ii){_ii.value=_ee.name+'：';_ii.focus()}};localStorage.removeItem('evo_active_expert')}catch(_ex){}};if(!_checkExpert()){var gg=document.getElementById('greeting');if(gg)gg.textContent=__('greeting').replace('{name}',localStorage.getItem('evo_user')||'')};restoreHistory();setTimeout(function(){checkLLM()},1000)}
function _checkExpert(){try{var e=localStorage.getItem('evo_active_expert');if(!e)return false;var x=JSON.parse(e);if(!x||!x.name){localStorage.removeItem('evo_active_expert');return false};localStorage.removeItem('evo_active_expert');var sys='你现在是 '+x.name+'（'+(x.dept||'')+'）。你是这个领域的专家，请始终保持这个角色身份回答问题。';try{CTX=CTX||[]}catch(ex){CTX=[]};CTX.push({role:'system',content:sys});try{CHAT=CHAT||[]}catch(ex){CHAT=[]};addMsg('🎯 已激活专家: '+x.name+'（'+(x.dept||'')+'）', 'bot');var inp=document.getElementById('input');if(inp){inp.value=x.name+'：';inp.focus();var isEnter=function(e){if(e.key==='Enter')send()};inp.onkeydown=isEnter;alert('_checkExpert: 已设值 '+x.name)};return true}catch(ee){alert('_checkExpert错误: '+ee);return false}
}

