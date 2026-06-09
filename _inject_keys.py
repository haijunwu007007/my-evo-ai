"""批量注入DeepSeek Key到agent_*.py文件"""
import os, re

BASE = "D:/AUTO-EVO-AI-V0.1/api/agents"
DEFAULT_KEY = "sk-e7a7f4e700d847f28027c5608e3f5c02"
KEY_INJECT = f'_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or "{DEFAULT_KEY}"\n_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"\n_LLM_MODEL = "deepseek-chat"\n'

# 需要注入的工具模块列表（高频使用）
files_to_inject = [
    "agent_s2c.py", "agent_chat2db.py", "agent_bolt.py", "agent_claude.py",
    "agent_legal.py", "agent_pra.py", "agent_qodo.py", "agent_aider.py",
    "agent_agentk8s.py", "agent_gptpilot.py", "agent_swe.py", "agent_agenteval.py",
    "agent_autogpt.py", "agent_openmanus.py", "agent_chatdev.py", "agent_tts.py",
    "agent_lida.py", "agent_paddleocr.py", "agent_interpreter.py", "agent_scrapegraphai.py",
    "agent_markitdown.py", "agent_openclaw.py", "agent_zen.py", "agent_shannon.py",
    "agent_openant.py", "agent_twenty.py", "agent_invoice.py", "agent_chatwoot.py",
    "agent_mermaid.py",
]

injected = 0
for fname in files_to_inject:
    fp = os.path.join(BASE, fname)
    if not os.path.exists(fp):
        continue
    content = open(fp, encoding='utf-8').read()
    # 如果还没有_LLM_ENDPOINT，则注入
    if '_LLM_ENDPOINT' not in content:
        # 在import部分后插入
        import_end = 0
        for m in re.finditer(r'^(import |from )', content, re.MULTILINE):
            import_end = m.start()
        # 找到最后一个import行
        lines = content.split('\n')
        last_import = -1
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')):
                last_import = i
        if last_import >= 0:
            lines.insert(last_import + 1, 'import os')
            lines.insert(last_import + 2, KEY_INJECT.strip())
            content = '\n'.join(lines)
            open(fp, 'w', encoding='utf-8').write(content)
            injected += 1
            print(f"  ✅ {fname}")

print(f"\n注入完成: {injected}/{len(files_to_inject)} 个文件")
