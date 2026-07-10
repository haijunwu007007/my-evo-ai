"""Aider — AI配对编程（文件级代码修改）"""
import logging
logger = logging.getLogger("evo.agent_aider")

import os, json, subprocess, tempfile
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def aider_edit(file_path: str = "", instruction: str = "", output_dir: str = "") -> dict:
    """用AI修改代码文件
    Args:
        file_path: 要修改的文件路径
        instruction: 自然语言描述要做什么修改
        output_dir: 输出目录
    Returns:
        {"success": bool, "diff": str, "output": str, "error": str}
    """
    if not file_path:
        return {"success": False, "error": "请提供 file_path"}
    if not instruction:
        return {"success": False, "error": "请提供 instruction"}

    fp = Path(file_path)
    if not fp.exists():
        return {"success": False, "error": f"文件不存在: {file_path}"}

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "需要设置 OPENAI_API_KEY"}

    try:
        # 尝试使用 aider 库
        try:
            from aider.coders import Coder
            from aider.models import Model
            from aider.io import InputOutput

            model = Model("gpt-4-turbo")
            io = InputOutput(yes=True, pretty=False)
            coder = Coder.create(main_model=model, io=io, fnames=[file_path])
            # aider 直接修改文件，然后读取 diff
            coder.run(instruction)
            
            # 获取 git diff
            import subprocess
            repo_dir = Path(file_path).parent
            diff_r = subprocess.run(["git", "diff", "--", file_path], 
                                    cwd=repo_dir, capture_output=True, text=True, timeout=10)
            diff = diff_r.stdout or "文件已修改（无 git diff 信息）"

            return {"success": True, "diff": diff, "file": file_path, "instruction": instruction}

        except ImportError:
            # 如果 aider 库不可用，用 LLM 直接修改代码
            from api.agent_llm import call_llm
            
            original_code = fp.read_text(encoding='utf-8')
            edit_prompt = f"""你是一个代码编辑专家。根据指令修改代码。

指令: {instruction}

当前代码:
```python
{original_code[:8000]}
```

输出修改后的完整代码（不是diff，是完整文件内容）在 ``` 代码块中。"""

            messages = [{"role": "system", "content": "你是一个代码编辑专家。输出完整代码。"},
                       {"role": "user", "content": edit_prompt}]
            content, _ = call_llm(messages, None, api_key)

            if not content:
                return {"success": False, "error": "代码修改失败"}

            import re
            code_blocks = re.findall(r'```\w*\n(.*?)```', content, re.DOTALL)
            new_code = code_blocks[0].strip() if code_blocks else content.strip()

            # 备份原文件
            backup_path = str(fp) + ".bak"
            fp.rename(backup_path)
            fp.write_text(new_code, encoding='utf-8')

            # 生成 diff
            diff_lines = []
            orig_lines = Path(backup_path).read_text(encoding='utf-8').splitlines()
            new_lines = new_code.splitlines()
            import difflib
            diff = '\n'.join(list(difflib.unified_diff(orig_lines, new_lines, fromfile=str(fp), tofile=str(fp), lineterm='')))

            return {"success": True, "diff": diff, "file": file_path, "backup": backup_path}

    except Exception as e:
        return {"success": False, "error": f"Aider操作失败: {e}"}
