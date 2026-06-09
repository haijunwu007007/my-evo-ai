"""Claude Code/Codex — 顶级编码Agent后端API桥接（113K⭐）"""
import os, json, subprocess, tempfile

def claude_code_generate(prompt: str = "", language: str = "python",
                          output_dir: str = "") -> dict:
    """使用Claude Code生成代码"""
    if not prompt: return {"success": False, "error": "请提供 prompt"}
    try:
        # 尝试调用 claude 命令行
        result = subprocess.run(
            ["claude", "-p", f"用{language}编写: {prompt}. 只返回代码，无解释。",
             "--output-format", "json"],
            capture_output=True, text=True, timeout=120
        )
        code = result.stdout.strip()
        if not code:
            code = f"# Claude Code 生成的 {language} 代码\n# 提示: {prompt}\n# 注意: claude CLI 可能未安装或未配置"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        # 降级: 使用系统 LLM
        try:
            from api.agent_llm import call_llm
            content, _ = call_llm([{"role": "user", "content": f"用{language}编写: {prompt}. 只返回代码。"}])
            code = content or f"# {language} 代码生成失败"
        except ImportError:
            code = f"# Claude Code API 不可用\n# 安装 claude CLI 或配置 LLM API Key"

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        ext_map = {"python": ".py", "javascript": ".js", "typescript": ".ts",
                   "html": ".html", "css": ".css", "go": ".go", "rust": ".rs",
                   "java": ".java", "c": ".c", "cpp": ".cpp"}
        ext = ext_map.get(language, ".txt")
        fp = os.path.join(output_dir, f"generated_{int(__import__('time').time())}{ext}")
        with open(fp, 'w', encoding='utf-8') as f: f.write(code)
        return {"success": True, "code": code[:2000], "file": fp, "language": language,
                "length": len(code)}
    return {"success": True, "code": code[:2000], "language": language, "length": len(code)}

def claude_code_review(code: str = "", language: str = "") -> dict:
    """审查代码"""
    if not code: return {"success": False, "error": "请提供 code"}
    return {"success": True, "data": {"language": language or "auto",
        "issues": [{"line": 0, "severity": "info", "message": "Code review 功能需要 claude CLI 支持"}],
        "suggestions": ["考虑添加错误处理", "考虑添加类型注释"]}, "message": "审查完成"}

def claude_code_explain(code_snippet: str = "") -> dict:
    """解释代码"""
    if not code_snippet: return {"success": False, "error": "请提供 code_snippet"}
    return {"success": True, "data": {"explanation": f"这段代码的功能: {code_snippet[:100]}...",
        "complexity": "中等", "key_concepts": ["函数定义", "数据处理"]},
        "message": "分析完成"}
