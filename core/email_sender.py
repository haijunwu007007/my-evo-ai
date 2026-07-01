'''
Email sender - 支持用户自配 SMTP
'''
import smtplib, json
from email.mime.text import MIMEText
from pathlib import Path

_CFG_FILE = Path(__file__).parent.parent / 'data' / 'smtp_config.json'

def _load_cfg():
    try:
        if _CFG_FILE.exists():
            return json.loads(_CFG_FILE.read_text())
    except: pass
    return {}

def _save_cfg(cfg):
    _CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CFG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))

def get_config():
    return _load_cfg()

def save_config(host, port, user, password, from_addr=''):
    cfg = {'host': host, 'port': int(port), 'user': user, 'password': password, 'from_addr': from_addr or user}
    _save_cfg(cfg)
    return {'success': True}

def send_email(to, subject, body, smtp_cfg=None):
    if not smtp_cfg:
        smtp_cfg = _load_cfg()
    if not smtp_cfg or not smtp_cfg.get('host'):
        return {'success': False, 'error': 'SMTP not configured. Go to /settings to set up.'}
    msg = MIMEText(body, 'html' if '<html>' in body else 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = smtp_cfg.get('from_addr') or smtp_cfg.get('user', '')
    msg['To'] = to
    try:
        svr = smtplib.SMTP(smtp_cfg['host'], int(smtp_cfg.get('port', 587)))
        svr.starttls()
        if smtp_cfg.get('user'): svr.login(smtp_cfg['user'], smtp_cfg['password'])
        svr.sendmail(msg['From'], [to], msg.as_string())
        svr.quit()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def send_invite(email, inviter='admin', role='editor', smtp_cfg=None):
    body = f'''<html><body style="font-family:sans-serif;max-width:500px;margin:40px auto">
<h2>You are invited to AUTO-EVO-AI</h2>
<p><b>{inviter}</b> invited you to join the team.</p>
<p>Your role: <b>{role}</b></p>
<p style="margin-top:20px"><a href="https://autoevoai.com/register?email={email}" style="background:#4361ee;color:#fff;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:600">Accept Invitation</a></p>
<p style="margin-top:12px;color:#6b7280;font-size:12px">Or open: https://autoevoai.com/register?email={email}</p>
</body></html>'''
    return send_email(email, f'{inviter} invited you to AUTO-EVO-AI', body, smtp_cfg)
