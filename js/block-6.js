
var authToken = localStorage.getItem('evo_auth_token');
async function handleLogin() {
    var user = document.getElementById('login-user').value;
    var pass = document.getElementById('login-pass').value;
    try {
        var r = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:user,password:pass})});
        var d = await r.json();
        if (d.success && d.access_token) {
            authToken = d.access_token;
            localStorage.setItem('evo_auth_token', authToken);
            document.getElementById('login-overlay').style.display = 'none';
        } else {
            document.getElementById('login-error').textContent = d.detail || '登录失败';
            document.getElementById('login-error').style.display = 'block';
        }
    } catch(e) {
        document.getElementById('login-error').textContent = '连接失败';
        document.getElementById('login-error').style.display = 'block';
    }
}
function logout() {
    authToken = null;
    localStorage.removeItem('evo_auth_token');
    document.getElementById('login-overlay').style.display = 'block';
}
async function checkAuth() {
    try {
        var r = await fetch('/api/auth/status');
        var d = await r.json();
        if (d.enabled && !authToken) {
            document.getElementById('login-overlay').style.display = 'block';
            return false;
        }
    } catch(e) {}
    return true;
}
setTimeout(checkAuth, 500);
