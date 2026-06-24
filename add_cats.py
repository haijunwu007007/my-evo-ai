c = open('./frontend/chat.html', encoding='utf-8').read()

# Find the tools section - between tabs and input area
ti = c.index('<!-- 文档/办公 -->')
tj = c.index('<div class="input-area">')
tools_html = c[ti:tj]

# Get all tool items - each is on a line with onclick
lines = tools_html.split('\n')
cat_names = ['文档/办公','数据/分析','通信/协作','企业/管理','部署/运维','监控/工具','智能/生活','搜索/集成','其他']
new_lines = []
for l in lines:
    stripped = l.strip()
    # Check if this is a category header
    is_cat = False
    for cn in cat_names:
        if cn in stripped and ('<div' in stripped or 'class=' in stripped):
            is_cat = True
            break
    if is_cat:
        # Wrap the category header with cat-head
        # Find the displayed text
        import re
        m = re.search(r'([\u4e00-\u9fff/\u2000-\u206f]+)', stripped)
        cat_text = m.group(1) if m else '分类'
        # Replace: <div style="...">📋 文档/办公</div>
        # With: <div class="cat-head" onclick="toggleCat(this)"><span>📋 文档/办公</span><span class="cat-ico">&#9660;</span></div>
        prefix = stripped[:stripped.index('📋')] if '📋' in stripped else stripped[:stripped.index('📊')] if '📊' in stripped else stripped[:stripped.index('📱')] if '📱' in stripped else ''
        # Simple approach: replace the exact string
        pass

open('./frontend/chat.html', 'w', encoding='utf-8').write(c)
print('done')
