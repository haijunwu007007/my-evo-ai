// ── AUTO-EVO-AI 前端组件库 v1 ──
// 所有页面共享的通用组件
// 使用：<script src="/components.js"></script>

(function() {
  'use strict';

  // ── 1. 主题切换 ──
  // 在页面中加：<span id="themeBtn" onclick="Evo.toggleTheme()">🌙</span>
  window.Evo = window.Evo || {};

  Evo.toggleTheme = function() {
    var b = document.body;
    b.classList.toggle('dark');
    var isDark = b.classList.contains('dark');
    try { localStorage.setItem('evo_theme', isDark ? 'dark' : 'light'); } catch(e) {}
    var btn = document.getElementById('themeBtn');
    if (btn) btn.textContent = isDark ? '☀️' : '🌙';
  };

  Evo.initTheme = function() {
    var saved;
    try { saved = localStorage.getItem('evo_theme'); } catch(e) {}
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (saved === 'dark' || (!saved && prefersDark)) {
      document.body.classList.add('dark');
      var btn = document.getElementById('themeBtn');
      if (btn) btn.textContent = '☀️';
    }
  };

  // ── 2. Toast 通知 ──
  // Evo.toast('消息', 'ok|err|info', 3000)
  Evo.toast = function(msg, type, duration) {
    type = type || 'info';
    duration = duration || 3000;
    var el = document.createElement('div');
    el.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:99999;padding:10px 18px;border-radius:8px;font-size:14px;font-weight:500;box-shadow:0 4px 20px rgba(0,0,0,.2);transition:opacity .3s;max-width:360px;color:#fff;background:' +
      (type === 'err' ? '#ef4444' : type === 'ok' ? '#10b981' : '#4361ee');
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function() { el.style.opacity = '0'; }, duration - 300);
    setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, duration);
  };

  // ── 3. Tab 切换 ──
  // Evo.switchTab(tabEl, contentId)
  Evo.switchTab = function(el, id) {
    var parent = el.parentElement;
    if (!parent) return;
    parent.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
    el.classList.add('active');
    var container = parent.parentElement;
    container.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    var target = document.getElementById(id);
    if (target) target.classList.add('active');
  };

  // ── 4. Loading 状态 ──
  // Evo.showLoading(container) / Evo.hideLoading(container)
  Evo.showLoading = function(container) {
    if (!container) container = document.body;
    var el = document.createElement('div');
    el.className = 'evo-loading';
    el.style.cssText = 'display:flex;align-items:center;justify-content:center;padding:40px;color:var(--text3,#6b7280);font-size:14px';
    el.textContent = '⏳ 加载中...';
    container.appendChild(el);
    return el;
  };

  Evo.hideLoading = function(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  };

  // ── 5. 返回顶部 ──
  // Evo.scrollToTop(smooth)
  Evo.scrollToTop = function(smooth) {
    window.scrollTo({ top: 0, behavior: smooth !== false ? 'smooth' : 'auto' });
  };

  // ── 6. 格式化时间 ──
  // Evo.formatTime(date)
  Evo.formatTime = function(d) {
    if (!d) d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2,'0') + '-' +
      String(d.getDate()).padStart(2,'0') + ' ' +
      String(d.getHours()).padStart(2,'0') + ':' +
      String(d.getMinutes()).padStart(2,'0');
  };

  // ── 7. 复制到剪贴板 ──
  // Evo.copy(text)
  Evo.copy = function(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function() {
        Evo.toast('✅ 已复制', 'ok');
      }).catch(function() {
        fallbackCopy(text);
      });
    } else {
      fallbackCopy(text);
    }
    function fallbackCopy(t) {
      var ta = document.createElement('textarea');
      ta.value = t;
      ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); Evo.toast('✅ 已复制', 'ok'); } catch(e) {}
      document.body.removeChild(ta);
    }
  };

  // ── 8. 确认弹窗（替代 confirm） ──
  // Evo.confirm(msg, callback)
  Evo.confirm = function(msg, callback) {
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center';
    var box = document.createElement('div');
    box.style.cssText = 'background:var(--card,#fff);border-radius:12px;padding:24px;max-width:340px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,.2);text-align:center';
    var p = document.createElement('p');
    p.style.cssText = 'margin:0 0 20px;font-size:15px;color:var(--text,#1a1a2e);line-height:1.5';
    p.textContent = msg;
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:10px;justify-content:center';
    var cancelBtn = document.createElement('button');
    cancelBtn.textContent = '取消';
    cancelBtn.style.cssText = 'padding:8px 20px;border-radius:8px;border:1px solid var(--border,#e8eaed);background:transparent;color:var(--text2,#6b7280);cursor:pointer;font-size:14px';
    var okBtn = document.createElement('button');
    okBtn.textContent = '确认';
    okBtn.style.cssText = 'padding:8px 20px;border-radius:8px;border:none;background:var(--accent,#4361ee);color:#fff;cursor:pointer;font-size:14px;font-weight:600';
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(okBtn);
    box.appendChild(p);
    box.appendChild(btnRow);
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    function close(result) {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      if (callback) callback(result);
    }
    cancelBtn.onclick = function() { close(false); };
    okBtn.onclick = function() { close(true); };
    overlay.onclick = function(e) { if (e.target === overlay) close(false); };
  };

  // ── 初始化 ──
  // DOM 加载完成后自动初始化主题
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', Evo.initTheme);
  } else {
    Evo.initTheme();
  }

})();
