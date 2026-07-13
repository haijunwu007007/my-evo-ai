(function(){
window.showToast = function(msg, type) {
  var t = document.createElement('div');
  t.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:10px 20px;border-radius:8px;color:#fff;z-index:99999;font-size:13px;background:' + (type === 'error' ? '#ef4444' : '#10b981') + ';box-shadow:0 4px 12px rgba(0,0,0,.2)';
  t.textContent = msg; document.body.appendChild(t);
  setTimeout(function(){ t.style.opacity = '0'; setTimeout(function(){ t.remove(); }, 300); }, 3000);
};
window.confirmDialog = function(msg, cb) { if(confirm(msg)) cb(); };
})();
