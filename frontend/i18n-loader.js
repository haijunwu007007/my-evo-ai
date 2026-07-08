/* AUTO-EVO-AI i18n 加载器 — 注入 __() 全局函数 */
(function() {
  var _lang = localStorage.getItem('evo_lang') || 'zh-CN';
  var _data = {};

  function loadI18n() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/v1/i18n?lang=' + _lang, true);
    xhr.onload = function() {
      if (xhr.status === 200) {
        var resp = JSON.parse(xhr.responseText);
        _data = resp.data || {};
        window.__i18n_lang = resp.lang;
        document.documentElement.lang = resp.lang === 'en-US' ? 'en' : 'zh-CN';
      }
    };
    xhr.send();
  }

  window.__ = function(key, fallback) {
    return _data[key] || fallback || key;
  };

  window.switchLang = function(lang) {
    _lang = lang;
    localStorage.setItem('evo_lang', lang);
    loadI18n();
    // 刷新页面上所有 __() 调用
    document.querySelectorAll('[data-i18n]').forEach(function(el) {
      var key = el.getAttribute('data-i18n');
      el.textContent = window.__(key, el.textContent);
    });
  };

  loadI18n();
})();
