
/* ─── SETUP WIZARD LOGIC ─── */
var SW_STEPS = ['welcome', 'ai', 'notify', 'schedule', 'complete'];
var swStep = 0;
var swData = {};
var swChecked = {};

/* 检测是否应该显示向导 */
function checkSetupWizard() {
  fetch('/api/config/items?group=llm').then(r => r.json()).then(data => {
    var items = data.items || [];
    var hasKey = items.some(i => i.key && i.value && i.value.length > 10 && !i.value.startsWith('sk-') === false || (i.value && i.value.length > 10));
    // Show wizard on first visit (no llm config saved)
    var wizardDone = localStorage.getItem('evo_setup_wizard_done');
    if (wizardDone === 'true') return;
    showSetupWizard();
  }).catch(() => {});
}

function showSetupWizard() {
  document.getElementById('setup-wizard-overlay').style.display = 'flex';
  swStep = 0;
  swData = { llm: {}, notify: {}, schedule: {} };
  swChecked = {};
  swRender();
}

function hideSetupWizard() {
  document.getElementById('setup-wizard-overlay').style.display = 'none';
  localStorage.setItem('evo_setup_wizard_done', 'true');
}

function swRender() {
  var step = SW_STEPS[swStep];
  var body = document.getElementById('swBody');
  var fill = document.getElementById('swProgressFill');
  var pct = ((swStep + 1) / SW_STEPS.length * 100) + '%';
  fill.style.width = pct;

  document.getElementById('swBtnSkip').style.display = ['welcome','complete'].includes(step) ? 'none' : 'inline-block';
  document.getElementById('swBtnBack').style.display = swStep > 0 && swStep < SW_STEPS.length - 1 ? 'inline-block' : 'none';
  document.getElementById('swBtnNext').style.display = step === 'complete' ? 'none' : 'inline-block';
  document.getElementById('swBtnFinish').style.display = step === 'complete' ? 'inline-block' : 'none';

  var renderers = { welcome: swRenderWelcome, ai: swRenderAI, notify: swRenderNotify, schedule: swRenderSchedule, complete: swRenderComplete };
  if (renderers[step]) renderers[step](body);
}

/* ── Step 0: Welcome ── */
function swRenderWelcome(el) {
  el.innerHTML = `
    <div class="sw-welcome-icon">🚀</div>
    <div class="sw-welcome-title">欢迎使用 AUTO-EVO-AI</div>
    <div class="sw-welcome-desc">
      智能自动化平台已就绪，535个功能模块 + 16个核心引擎<br>
      只需几步配置即可激活全部能力
    </div>
    <div class="sw-welcome-features">
      <div class="sw-wf-item"><div class="swf-icon">🧠</div><div class="swf-text">AI智能引擎</div></div>
      <div class="sw-wf-item"><div class="swf-icon">📡</div><div class="swf-text">多渠道推送</div></div>
      <div class="sw-wf-item"><div class="swf-icon">⏰</div><div class="swf-text">定时自动化</div></div>
      <div class="sw-wf-item"><div class="swf-icon">⚡</div><div class="swf-text">事件驱动</div></div>
    </div>`;
}

/* ── Step 1: AI Provider ── */
function swRenderAI(el) {
  el.innerHTML = `
    <div class="sw-group-title">🧠 AI 服务配置</div>
    <div class="sw-group-desc">至少配置1个AI服务即可激活智能能力（推荐DeepSeek，性价比最高）</div>
    <div class="sw-field">
      <label>DeepSeek API Key <span class="req">*</span></label>
      <input type="password" id="sw_deepseek_key" placeholder="sk-xxxxxxxxxxxxxxxx" oninput="swValidateAI()">
      <div class="sw-hint"><a href="https://platform.deepseek.com/api_keys" target="_blank">platform.deepseek.com</a> — 注册即送500万Token</div>
      <div id="sw_deepseek_msg"></div>
    </div>
    <div class="sw-field">
      <label>智谱AI (GLM) API Key</label>
      <input type="password" id="sw_zhipu_key" placeholder="xxxxxxxxxxxxxxxx.xxxxxx" oninput="swValidateAI()">
      <div class="sw-hint"><a href="https://open.bigmodel.cn" target="_blank">open.bigmodel.cn</a> — 新用户送免费额度</div>
      <div id="sw_zhipu_msg"></div>
    </div>
    <div class="sw-field">
      <label>OpenAI API Key</label>
      <input type="password" id="sw_openai_key" placeholder="sk-xxxxxxxxxxxxxxxx" oninput="swValidateAI()">
      <div class="sw-hint">国际版OpenAI，需海外网络访问</div>
      <div id="sw_openai_msg"></div>
    </div>
    <div class="sw-field">
      <label>Anthropic API Key</label>
      <input type="password" id="sw_anthropic_key" placeholder="sk-ant-xxxxxxxxxxxxxxxx" oninput="swValidateAI()">
      <div class="sw-hint">Claude系列模型</div>
      <div id="sw_anthropic_msg"></div>
    </div>
    <div class="sw-field">
      <label>Google Gemini API Key</label>
      <input type="password" id="sw_gemini_key" placeholder="AIzaSyxxxxxxxxxxxxxxxx" oninput="swValidateAI()">
      <div class="sw-hint">Google AI Studio免费获取</div>
      <div id="sw_gemini_msg"></div>
    </div>
    <div class="sw-field">
      <label>Ollama 本地模型</label>
      <input type="text" id="sw_ollama_url" value="http://127.0.0.1:11434" placeholder="http://127.0.0.1:11434">
      <div class="sw-hint">本地运行Ollama后自动可用，无需API Key</div>
    </div>`;
  swValidateAI();
}

function swValidateAI() {
  var d = document.getElementById('sw_deepseek_key').value.trim();
  var z = document.getElementById('sw_zhipu_key').value.trim();
  var o = document.getElementById('sw_openai_key').value.trim();
  var a = document.getElementById('sw_anthropic_key').value.trim();
  var g = document.getElementById('sw_gemini_key').value.trim();
  swData.llm = {};
  if (d.length > 10) { swData.llm.deepseek_api_key = d; swSetMsg('sw_deepseek_msg','ok','✓ Key格式正确'); } else { swSetMsg('sw_deepseek_msg',''); }
  if (z.length > 10) { swData.llm.zhipu_api_key = z; swSetMsg('sw_zhipu_msg','ok','✓ Key格式正确'); } else { swSetMsg('sw_zhipu_msg',''); }
  if (o.length > 10) { swData.llm.openai_api_key = o; swSetMsg('sw_openai_msg','ok','✓ Key格式正确'); } else { swSetMsg('sw_openai_msg',''); }
  if (a.length > 10) { swData.llm.anthropic_api_key = a; swSetMsg('sw_anthropic_msg','ok','✓ Key格式正确'); } else { swSetMsg('sw_anthropic_msg',''); }
  if (g.length > 10) { swData.llm.gemini_api_key = g; swSetMsg('sw_gemini_msg','ok','✓ Key格式正确'); } else { swSetMsg('sw_gemini_msg',''); }
  swData.llm.ollama_base_url = document.getElementById('sw_ollama_url').value.trim();
}

function swSetMsg(id, type, text) {
  var el = document.getElementById(id);
  if (!el) return;
  el.className = type === 'ok' ? 'sw-ok' : type === 'err' ? 'sw-err' : '';
  el.textContent = text || '';
}

/* ── Step 2: Notification ── */
function swRenderNotify(el) {
  el.innerHTML = `
    <div class="sw-group-title">📡 消息推送配置</div>
    <div class="sw-group-desc">配置后系统告警和自动化报告将通过这些渠道推送</div>
    <div class="sw-field">
      <label>企业微信 Webhook</label>
      <input type="text" id="sw_wecom_webhook" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx">
      <div class="sw-hint">群聊 → 添加群机器人 → 复制Webhook地址</div>
    </div>
    <div class="sw-field">
      <label>钉钉机器人 Webhook</label>
      <input type="text" id="sw_dingtalk_webhook" placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx">
      <div class="sw-hint">群设置 → 智能群助手 → 添加机器人 → 安全设置</div>
    </div>
    <div class="sw-field">
      <label>钉钉签名密钥 (Secret)</label>
      <input type="password" id="sw_dingtalk_secret" placeholder="SECxxxxxxxxxxxxxxxx">
      <div class="sw-hint">钉钉安全设置选择"加签"时需要填写</div>
    </div>
    <div class="sw-field">
      <label>飞书 Webhook</label>
      <input type="text" id="sw_feishu_webhook" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx">
      <div class="sw-hint">群设置 → 群机器人 → 添加自定义机器人</div>
    </div>
    <div class="sw-field">
      <label>Server酱 SendKey</label>
      <input type="text" id="sw_serverchan_key" placeholder="SCTxxxxxxxxxxxxxx">
      <div class="sw-hint"><a href="https://sct.ftqq.com" target="_blank">sct.ftqq.com</a> — 微信扫码登录，30秒获取</div>
    </div>
    <div class="sw-field">
      <label>Bark URL (iPhone)</label>
      <input type="text" id="sw_bark_url" placeholder="https://api.day.app/your-key/">
      <div class="sw-hint">App Store下载Bark App → 复制推送URL</div>
    </div>
    <div class="sw-field">
      <label>PushPlus Token</label>
      <input type="text" id="sw_pushplus_token" placeholder="xxxxxxxxxxxxxxxx">
      <div class="sw-hint"><a href="https://www.pushplus.plus" target="_blank">pushplus.plus</a> — 微信扫码登录</div>
    </div>
    <div class="sw-field">
      <label>自定义 Webhook (JSON POST)</label>
      <input type="text" id="sw_custom_webhook" placeholder="https://your-domain.com/webhook">
      <div class="sw-hint">系统将以POST JSON格式发送 {title, message, level, timestamp}</div>
    </div>`;
}

/* ── Step 3: Schedule & Events ── */
function swRenderSchedule(el) {
  el.innerHTML = `
    <div class="sw-group-title">⏰ 自动化调度</div>
    <div class="sw-group-desc">启用后会自动创建定时任务和事件规则</div>
    <div class="sw-toggle-row">
      <div class="sw-toggle-info">
        <div class="stl-name">🔍 系统健康巡检</div>
        <div class="stl-desc">每6小时自动检查CPU/内存/模块状态</div>
      </div>
      <label class="sw-toggle-switch"><input type="checkbox" id="sw_sched_health" checked><span class="slider"></span></label>
    </div>
    <div class="sw-toggle-row">
      <div class="sw-toggle-info">
        <div class="stl-name">🛡️ 安全扫描</div>
        <div class="stl-desc">每天08:00自动扫描安全威胁</div>
      </div>
      <label class="sw-toggle-switch"><input type="checkbox" id="sw_sched_security" checked><span class="slider"></span></label>
    </div>
    <div class="sw-toggle-row">
      <div class="sw-toggle-info">
        <div class="stl-name">📊 性能报告</div>
        <div class="stl-desc">每天20:00自动采集性能数据</div>
      </div>
      <label class="sw-toggle-switch"><input type="checkbox" id="sw_sched_perf" checked><span class="slider"></span></label>
    </div>
    <div class="sw-toggle-row">
      <div class="sw-toggle-info">
        <div class="stl-name">🧹 日志清理</div>
        <div class="stl-desc">每周日凌晨2:00自动清理过期日志</div>
      </div>
      <label class="sw-toggle-switch"><input type="checkbox" id="sw_sched_log" checked><span class="slider"></span></label>
    </div>
    <div class="sw-toggle-row">
      <div class="sw-toggle-info">
        <div class="stl-name">📁 文件变化监听</div>
        <div class="stl-desc">监听日志和模块文件变化，自动触发事件</div>
      </div>
      <label class="sw-toggle-switch"><input type="checkbox" id="sw_sched_filewatch" checked><span class="slider"></span></label>
    </div>
    <div class="sw-toggle-row">
      <div class="sw-toggle-info">
        <div class="stl-name">🔔 异常自动告警</div>
        <div class="stl-desc">模块失败/CPU过高/安全威胁自动推送通知</div>
      </div>
      <label class="sw-toggle-switch"><input type="checkbox" id="sw_sched_alert" checked><span class="slider"></span></label>
    </div>`;
}

/* ── Step 4: Complete ── */
function swRenderComplete(el) {
  var aiCount = Object.keys(swData.llm || {}).filter(k => !k.includes('url')).length;
  var notifyKeys = ['wecom_webhook','dingtalk_webhook','feishu_webhook','serverchan_key','bark_url','pushplus_token','custom_webhook'];
  var notifyCount = notifyKeys.filter(k => swData.notify[k] && swData.notify[k].length > 5).length;
  var schedChecked = (['sched_health','sched_security','sched_perf','sched_log','sched_filewatch','sched_alert']).filter(id => {
    var el = document.getElementById('sw_' + id);
    return el && el.checked;
  }).length;

  el.innerHTML = `
    <div class="sw-complete-icon">🎉</div>
    <div class="sw-complete-title">配置完成！</div>
    <div class="sw-complete-desc">系统已准备就绪，以下能力已激活</div>
    <div class="sw-complete-stats">
      <div class="sw-cs-item"><div class="scs-num">${aiCount}</div><div class="scs-label">AI 服务</div></div>
      <div class="sw-cs-item"><div class="scs-num">${notifyCount}</div><div class="scs-label">推送渠道</div></div>
      <div class="sw-cs-item"><div class="scs-num">${schedChecked}</div><div class="scs-label">自动任务</div></div>
    </div>
    <div class="sw-complete-desc">
      ${aiCount === 0 ? '⚠️ 未配置AI服务，智能能力暂不可用<br>' : ''}
      ${notifyCount === 0 ? '⚠️ 未配置推送渠道，告警通知暂不可用<br>' : ''}
      ${aiCount > 0 || notifyCount > 0 ? '您可以随时在「配置中心」中修改这些设置' : '建议至少配置1个AI服务以激活智能能力'}
    </div>`;
}

/* ── Navigation ── */
async function swNext() {
  var step = SW_STEPS[swStep];
  if (step === 'ai') {
    swData.llm = {};
    var d = document.getElementById('sw_deepseek_key').value.trim();
    var z = document.getElementById('sw_zhipu_key').value.trim();
    var o = document.getElementById('sw_openai_key').value.trim();
    var a = document.getElementById('sw_anthropic_key').value.trim();
    var g = document.getElementById('sw_gemini_key').value.trim();
    var ou = document.getElementById('sw_ollama_url').value.trim();
    if (d) swData.llm.deepseek_api_key = d;
    if (z) swData.llm.zhipu_api_key = z;
    if (o) swData.llm.openai_api_key = o;
    if (a) swData.llm.anthropic_api_key = a;
    if (g) swData.llm.gemini_api_key = g;
    if (ou) swData.llm.ollama_base_url = ou;
    // Save to backend
    if (Object.keys(swData.llm).length > 0) {
      await swSaveBatch(swData.llm, 'llm');
    }
  } else if (step === 'notify') {
    swData.notify = {
      wecom_webhook: document.getElementById('sw_wecom_webhook').value.trim(),
      dingtalk_webhook: document.getElementById('sw_dingtalk_webhook').value.trim(),
      dingtalk_secret: document.getElementById('sw_dingtalk_secret').value.trim(),
      feishu_webhook: document.getElementById('sw_feishu_webhook').value.trim(),
      serverchan_key: document.getElementById('sw_serverchan_key').value.trim(),
      bark_url: document.getElementById('sw_bark_url').value.trim(),
      pushplus_token: document.getElementById('sw_pushplus_token').value.trim(),
      custom_webhook: document.getElementById('sw_custom_webhook').value.trim(),
    };
    var filled = Object.values(swData.notify).filter(v => v && v.length > 3);
    if (filled.length > 0) {
      await swSaveBatch(swData.notify, 'notify');
    }
  } else if (step === 'schedule') {
    swData.schedule = {
      health: document.getElementById('sw_sched_health').checked,
      security: document.getElementById('sw_sched_security').checked,
      perf: document.getElementById('sw_sched_perf').checked,
      log: document.getElementById('sw_sched_log').checked,
      filewatch: document.getElementById('sw_sched_filewatch').checked,
      alert: document.getElementById('sw_sched_alert').checked,
    };
    await swApplySchedules();
  }
  if (swStep < SW_STEPS.length - 1) { swStep++; swRender(); }
}

function swBack() {
  if (swStep > 0) { swStep--; swRender(); }
}

function swSkip() {
  if (swStep < SW_STEPS.length - 1) { swStep++; swRender(); }
}

async function swFinish() { hideSetupWizard(); }

/* ── Save config to backend ── */
async function swSaveBatch(data, group) {
  for (const [key, value] of Object.entries(data)) {
    if (!value) continue;
    try {
      await fetch('/api/config/items/' + key, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: value, group: group, sensitive: key.toLowerCase().includes('key') || key.toLowerCase().includes('secret') || key.toLowerCase().includes('token') })
      });
    } catch(e) { console.warn('Config save error:', key, e); }
  }
}

async function swApplySchedules() {
  // Schedules are already pre-configured in backend, toggles just enable/disable
  var toggles = swData.schedule;
  var tasks = [
    { id: 'system_health_check', key: 'health' },
    { id: 'security_daily_scan', key: 'security' },
    { id: 'performance_report_daily', key: 'perf' },
    { id: 'log_cleanup_weekly', key: 'log' },
  ];
  for (var t of tasks) {
    if (!toggles[t.key]) {
      try { await fetch('/api/scheduler/tasks/' + t.id + '/toggle', { method: 'POST' }); } catch(e) {}
    }
  }
}

/* Auto-show on load */
setTimeout(checkSetupWizard, 1500);
