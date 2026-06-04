/* AUTO-EVO-AI i18n 加载器 + 主题切换 */
(function(){
  /* === i18n === */
  window._LANG = localStorage.getItem('evo_locale') || 'zh-CN';
  window._I18N = {};
  
  async function loadI18n(lang) {
    try {
      var r = await fetch('/api/v1/i18n?lang=' + (lang || _LANG));
      var d = await r.json();
      if (d.success) { _I18N = d.data || {}; _LANG = d.lang; localStorage.setItem('evo_locale', _LANG); }
    } catch(e) { _I18N = {}; }
    
    // 更新语言选择器
    var sel = document.getElementById('langSelect') || document.querySelector('.lang-select');
    if (sel) sel.value = _LANG;
    
    // 翻译 data-i18n 元素
    document.querySelectorAll('[data-i18n]').forEach(function(el) {
      var k = el.getAttribute('data-i18n');
      var t = _I18N[k] || k;
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = t;
      else if (k === 'greeting') el.textContent = t.replace('{name}', localStorage.getItem('evo_user') || '');
      else el.textContent = t;
    });
    
    // 翻译 document title
    if (_I18N.title) document.title = _I18N.title;
  }
  
  window.__ = function(k) { var v = _I18N[k]; return v !== undefined ? v : k; };
  window.setLocale = function(c) { _LANG = c; localStorage.setItem('evo_locale', c); loadI18n(c); };
  
  /* === 主题切换 === */
  var _THEME = localStorage.getItem('evo_theme') || 'dark';
  function applyTheme(t) {
    _THEME = t; localStorage.setItem('evo_theme', t);
    document.documentElement.setAttribute('data-theme', t);
    // 注入主题 CSS 变量
    var s = document.getElementById('theme-vars');
    if (!s) { s = document.createElement('style'); s.id = 'theme-vars'; document.head.appendChild(s); }
    if (t === 'dark') {
      s.textContent = ':root{--bg:#0f0f1a;--card:#1a1a2e;--text:#e0e0e0;--text2:#8892b0;--border:#2d3561;--accent:#4361ee}';
    } else {
      s.textContent = ':root{--bg:#f5f5f7;--card:#ffffff;--text:#1a1a2e;--text2:#6b7280;--border:#e5e7eb;--accent:#4361ee}';
    }
    // 更新toggle按钮
    var tb = document.getElementById('themeToggle');
    if (tb) tb.textContent = t === 'dark' ? '☀️' : '🌙';
  }
  window.toggleTheme = function() { applyTheme(_THEME === 'dark' ? 'light' : 'dark'); };
  
  // 注入主题 toggle 按钮
  document.addEventListener('DOMContentLoaded', function() {
    applyTheme(_THEME);
    if (!document.getElementById('themeToggle')) {
      var btn = document.createElement('button');
      btn.id = 'themeToggle'; btn.textContent = '☀️';
      btn.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:9999;width:40px;height:40px;border-radius:50%;border:none;background:var(--card);color:var(--text);cursor:pointer;font-size:18px;box-shadow:0 2px 8px rgba(0,0,0,.3);transition:all .3s';
      btn.onclick = window.toggleTheme;
      document.body.appendChild(btn);
    }
  });
  
  // 加载 i18n
  loadI18n();
})();
