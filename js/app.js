/* AUTO-EVO-AI 共享JS库 — 所有页面共用 */
(function(w){
  var APP = w.EVO = w.EVO || {};

  // 导航栏高亮
  APP.highlightNav = function(){
    var path = w.location.pathname;
    document.querySelectorAll('.hdr .n a').forEach(function(a){
      var href = a.getAttribute('href');
      a.className = (path === href || (href !== '/' && path.startsWith(href))) ? 'a' : '';
    });
  };

  // LLM状态标记
  APP.checkLLM = function(badgeId){
    var badge = document.getElementById(badgeId || 'modelBadge');
    if (!badge) return;
    badge.textContent = '\u23f3';
    var ctrl = new AbortController();
    setTimeout(function(){ ctrl.abort(); }, 5000);
    fetch('/api/v1/llm/status', {signal: ctrl.signal})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if (d && d.active && d.active.length > 0) badge.textContent = '\U0001f9e0 ' + d.active[0].name;
        else if (d && d.providers) {
          var a = d.providers.filter(function(p){ return p.available; });
          badge.textContent = '\U0001f9e0 ' + (a[0] ? a[0].name : '\u2716 \u65e0\u6a21\u578b');
        } else badge.textContent = '\u2716 \u65e0\u6a21\u578b';
      })
      .catch(function(){ badge.textContent = '\u2716 \u68c0\u6d4b\u5931\u8d25'; });
  };

  // 工具按钮通用
  APP.quickTool = function(name){
    if (w._TOOL_HINTS && w._TOOL_HINTS[name]) {
      var input = document.getElementById('input');
      if (input) { input.value = w._TOOL_HINTS[name]; input.focus(); }
    }
    if (typeof w.send === 'function') w.send();
  };

  // 工具搜索
  APP.filterTools = function(q){
    var btns = document.querySelectorAll('.quick-actions .qa, .tool-grid .tool-btn, .tool-item');
    var cnt = 0;
    q = (q || '').toLowerCase().trim();
    btns.forEach(function(b){
      var t = (b.textContent || '').toLowerCase();
      if (!q || t.indexOf(q) >= 0) { b.style.display = ''; cnt++; }
      else b.style.display = 'none';
    });
    var c = document.getElementById('toolCount');
    if (c) c.textContent = cnt + '/' + btns.length;
  };

  // 通用fetch封装
  APP.api = function(url, opts){
    opts = opts || {};
    return fetch(url, {
      method: opts.method || 'GET',
      headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      signal: opts.timeout ? AbortSignal.timeout(opts.timeout) : undefined
    }).then(function(r){ return r.json(); });
  };

  w.addEventListener('DOMContentLoaded', function(){
    APP.highlightNav();
    if (document.getElementById('modelBadge')) APP.checkLLM();
  });
})(window);
