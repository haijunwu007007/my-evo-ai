"""批量修复API Key硬编码：全部改为环境变量优先 + 安全fallback"""
import os, re

api_dir = r'D:\AUTO-EVO-AI-V0.1\api'
fixed = 0

for root, dirs, files in os.walk(api_dir):
    for f in files:
        if not f.endswith('.py'): continue
        fp = os.path.join(root, f)
        content = open(fp, 'r', encoding='utf-8').read()
        old = content

        # Pattern: _DEFAULT_KEY = os.environ.get(...) or "sk-e7a7..."
        content = re.sub(
            r'_DEFAULT_KEY = os\.environ\.get\("DEEPSEEK_API_KEY"\) or "sk-e7a7[^"]*"',
            r'_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""',
            content
        )

        # Pattern: _LLM_KEY = "sk-e7a7..."
        content = re.sub(
            r'_LLM_KEY = "sk-e7a7[^"]*"',
            r'_LLM_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""',
            content
        )

        # Pattern: "sk-e7a7..." used inline as string literal (only in routes_agents.py style)
        content = re.sub(
            r'os\.environ\.get\("DEEPSEEK_API_KEY"\) or os\.environ\.get\("OPENAI_API_KEY"\) or ""',
            r'os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""',
            content
        )

        if content != old:
            open(fp, 'w', encoding='utf-8').write(content)
            fixed += 1
            print(f'  FIXED: {os.path.relpath(fp, api_dir)}')

print(f'\nTotal: {fixed} files fixed')
