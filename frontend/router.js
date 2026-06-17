// SPA Router
const PAGES = {login: '/frontend/pages/login.html', dashboard: '/frontend/pages/dashboard.html', config: '/frontend/pages/config.html'};

function showPage(name) {
  const url = PAGES[name] || PAGES.login;
  fetch(url).then(r => r.text()).then(html => {
    const app = document.getElementById('app');
    if (app) app.innerHTML = html; else document.body.innerHTML = html;
    window.dispatchEvent(new CustomEvent('page-loaded', {detail: {page: name}}));
    history.replaceState({page: name}, '', '?page=' + name);
  });
}

// Init from URL
document.addEventListener('DOMContentLoaded', () => {
  const p = new URLSearchParams(location.search).get('page') || 'login';
  showPage(p);
});
