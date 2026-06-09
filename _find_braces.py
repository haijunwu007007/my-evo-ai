"""Find ALL unescaped { in SP f-string that are NOT valid format specs"""
with open('api/agent_core.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_sp = False
for i, line in enumerate(lines, start=1):
    if 'SP = f"""' in line:
        in_sp = True
        continue
    if in_sp and line.strip() == '"""':
        break
    if in_sp:
        s = line.strip()
        # Find any { that starts a JSON-like pattern but is not a format placeholder
        # In f-strings, {name} is format, {{ is escaped literal
        # Problem: {"provider" looks like format spec with "provider" key
        import re
        # Find single { followed by " or ' that are NOT part of {{ escape
        for m in re.finditer(r'(?<!\{)\{(["\'])', s):
            pos = m.start()
            context = s[max(0,pos-5):pos+30]
            print(f"L{i} pos={pos}: ...{context}...")
