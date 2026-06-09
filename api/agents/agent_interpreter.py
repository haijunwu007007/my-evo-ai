"""Open Interpreter — 自然语言电脑控制（读写文件/运行代码/操作终端）"""
import os, json
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def interpreter_execute(command: str = "", language: str = "python", timeout: int = 30) -> dict:
    """用自然语言控制电脑
    Args:
        command: 自然语言描述要做什么（如"帮我安装pandas并读取这个CSV"）
        language: 编程语言 (python/shell/javascript)
        timeout: 超时秒数
    Returns:
        {"success": bool, "output": str, "error": str}
    """
    try:
        from interpreter import interpreter
    except ImportError:
        return {"success": False, "error": "open-interpreter 未安装。运行: pip install open-interpreter"}

    if not command:
        return {"success": False, "error": "缺少 command 参数"}

    try:
        # 配置
        interpreter.llm.model = "gpt-4" if os.environ.get("OPENAI_API_KEY") else "gpt-3.5-turbo"
        interpreter.auto_run = True  # 自动执行，不等待确认
        interpreter.verbose = False

        # 执行
        result = interpreter.chat(command, display=False, stream=False)
        output = str(result) if result else ""
        return {"success": True, "output": output[:5000], "command": command}
    except Exception as e:
        return {"success": False, "error": f"执行失败: {e}"}

def interpreter_code(code: str = "", language: str = "python") -> dict:
    """直接执行代码片段"""
    try:
        from interpreter import interpreter
    except ImportError:
        return {"success": False, "error": "open-interpreter 未安装"}

    try:
        interpreter.auto_run = True
        interpreter.verbose = False
        result = interpreter.chat(f"执行以下{language}代码:\n```{language}\n{code}\n```", display=False, stream=False)
        output = str(result) if result else ""
        return {"success": True, "output": output[:5000]}
    except Exception as e:
        return {"success": False, "error": f"执行失败: {e}"}
