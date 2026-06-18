"""Bolt.new — 一句话生成并部署全栈应用"""
import os, json, time
from pathlib import Path
import os
# ⚠️ 安全提醒：优先通过环境变量 DEEPSEEK_API_KEY 传入 API Key
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def bolt_generate(prompt: str = "", framework: str = "vue", 
                  deploy: bool = False, output_dir: str = "") -> dict:
    """从描述生成完整Web应用
    Args:
        prompt: 应用描述（如"一个待办事项管理应用，支持增删改"）
        framework: 前端框架 (vue/react/svelte/html)
        deploy: 是否尝试部署
        output_dir: 输出目录
    Returns:
        {"success": bool, "files": list, "preview_url": str, "deploy_url": str}
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "需要设置 OPENAI_API_KEY"}

    if not prompt:
        return {"success": False, "error": "请提供 prompt"}

    try:
        from api.agent_llm import call_llm
        out_dir = Path(output_dir) if output_dir else Path("output/apps")
        out_dir.mkdir(parents=True, exist_ok=True)

        system_prompt = f"""你是一个全栈开发者。根据需求生成完整的{framework}应用代码。
输出一个HTML文件（包含CSS和JS内联）或前端组件。
要求: 现代设计、响应式、完整功能、生产质量。"""

        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"创建: {prompt}\n框架: {framework}\n输出完整代码在 ```html 代码块中。"}
        ]

        content, _ = call_llm(msgs, None, api_key)
        if not content:
            return {"success": False, "error": "生成失败"}

        import re
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', content, re.DOTALL)
        code = ""
        file_ext = ".html"
        for lang, block in code_blocks:
            block = block.strip()
            if lang in ("html", "svelte", "vue") or "doctype" in block.lower() or "<html" in block.lower():
                code = block
                file_ext = f".{lang}" if lang in ("html", "svelte", "vue") else ".html"
                break
        if not code:
            code = content.strip()
            # 尝试找到 HTML
            html_match = re.search(r'(<!DOCTYPE.*?</html>)', content, re.DOTALL | re.IGNORECASE)
            if html_match:
                code = html_match.group(1)

        fn = f"bolt_{int(time.time())}{file_ext}"
        fp = out_dir / fn
        fp.write_text(code, encoding='utf-8')

        deploy_url = ""
        if deploy:
            try:
                # 尝试写入一个简单的 index.html 并启动预览
                preview_path = out_dir / "index.html"
                preview_path.write_text(code, encoding='utf-8')
                deploy_url = f"/output/apps/{fn}"
            except Exception:
                pass

        return {
            "success": True,
            "files": [{"name": fn, "path": str(fp), "size": len(code)}],
            "preview_url": f"/output/apps/{fn}",
            "deploy_url": deploy_url or "手动部署",
            "summary": f"✅ {prompt[:30]} — 已生成"
        }

    except Exception as e:
        return {"success": False, "error": f"Bolt 生成失败: {e}"}
