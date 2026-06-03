import re, json

with open('frontend/i18n.js', 'r', encoding='utf-8') as f:
    src = f.read()

# 补充所有语言块的导航键
add_keys = {
    "tab_dashboard": "\"📊 仪表盘\"",
    "tab_business": "\"🏢 企业管理\"",
    "input_placeholder": "\"输入你想做的事...\"",
}

# 找到每个语言块末尾插入导航键
for lang in ['zh-CN','en','ja','ko']:
    # 先看是否已有 tab_dashboard
    if f"'{lang}'" not in src: continue
    if f'tab_dashboard' in src.split(f"'{lang}'")[1].split("},",1)[0]: continue
    # 在 name 行后插入
    src = src.replace(
        f"'{lang}': {{",
        f"'{lang}': {json.dumps(add_keys, ensure_ascii=False)[1:-1]},\n  " + "'zh-CN': {".split("'zh-CN': {")[1].split("\n")[0]
    )

print("done")
