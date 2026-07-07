"""Scan all sidebar-linked HTML pages for mobile adaptation gaps."""
import os, sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

DIR = r'D:\AUTO-EVO-AI-V0.1\frontend'

pages = [
    ('enterprise.html', '工作台'),
    ('agents.html', 'Agent集群'),
    ('skills.html', '技能扩展'),
    ('capabilities.html', '能力中心'),
    ('billion-os.html', '集团OS'),
    ('experts.html', '专家库'),
    ('claw.html', 'Open Claw'),
    ('human.html', 'Human'),
    ('hermes.html', 'Hermes'),
    ('admin.html', '管理中心'),
    ('automations.html', '自动化'),
    ('loop.html', '循环'),
    ('learn.html', '学习'),
    ('hub.html', '开源中心'),
    ('cognee.html', '记忆库'),
    ('deploy.html', '一键部署'),
    ('video.html', '视频生成'),
    ('agent.html', '本地代理'),
    ('settings.html', '系统设置'),
    ('apps.html', '已生成APP'),
    ('review.html', '版本差异'),
    ('dashboard.html', '系统状态'),
    ('canvas.html', '编排画布'),
]

print(f"{'页面':<24} {'viewport':<10} {'@media':<10} {'说明'}")
print('-' * 60)

for fn, label in pages:
    path = os.path.join(DIR, fn)
    if not os.path.exists(path):
        print(f"{label:<24} {'N/A':<10} {'N/A':<10} 文件不存在")
        continue
    
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    has_vp = 'name="viewport"' in content or "name='viewport'" in content
    has_mq = '@media' in content
    is_html = '<!DOCTYPE html>' in content.upper() or '<!doctype html>' in content.lower()
    
    issues = []
    if not has_vp: issues.append('缺viewport')
    if not has_mq: issues.append('缺@media')
    if not is_html: issues.append('非标准HTML')
    
    vp_s = 'OK' if has_vp else 'MISS'
    mq_s = 'OK' if has_mq else 'MISS'
    txt = ', '.join(issues) if issues else 'OK'
    
    print(f"{label:<24} {vp_s:<10} {mq_s:<10} {txt}")
