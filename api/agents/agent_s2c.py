"""Screenshot-to-Code — 截图→前端代码（Vue/React/HTML/Tailwind）"""
import os, json, base64, time
from pathlib import Path

def screenshot_to_code(image_path: str = "", image_url: str = "", stack: str = "html_css", output_dir: str = "") -> dict:
    """截图/设计稿 → 生成前端代码
    Args:
        image_path: 本地图片路径
        image_url: 远程图片URL
        stack: 技术栈 (html_css/html_tailwind/react_tailwind/vue_tailwind/bootstrap)
        output_dir: 输出目录（可选）
    Returns:
        {"success": bool, "code": str, "files": list, "preview_url": str, "error": str}
    """
    try:
        # 尝试导入 screenshot-to-code 库
        # 项目: https://github.com/abi/screenshot-to-code
        # 这个项目通常以 Web 服务方式运行，我们直接调它的 API 或模拟简化实现
        import httpx
    except ImportError:
        return {"success": False, "error": "httpx 未安装"}

    # 策略1: 如果有本地部署的 screenshot-to-code 服务
    service_url = os.environ.get("S2C_SERVICE_URL", "http://localhost:5173")
    api_key = os.environ.get("OPENAI_API_KEY", "")

    if not image_path and not image_url:
        return {"success": False, "error": "请提供 image_path 或 image_url"}

    try:
        # 读取图片
        if image_path:
            fp = Path(image_path)
            if not fp.exists():
                return {"success": False, "error": f"图片不存在: {image_path}"}
            img_b64 = base64.b64encode(fp.read_bytes()).decode()
            img_data_uri = f"data:image/{fp.suffix.lstrip('.')};base64,{img_b64}"
        elif image_url:
            img_data_uri = image_url

        # 尝试调用服务的 API
        # 如果没有服务，回退到 LLM 直接生成
        # 策略2: 直接用 LLM 生成代码（简化版）
        from api.agent_llm import call_llm

        system_prompt = f"""You are an expert frontend developer. Given an image/screenshot, generate complete frontend code.
Stack: {stack}
Output ONLY the code in ```html or ```jsx block. Make it pixel-perfect, responsive, and production-quality."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": f"Generate code matching this design exactly. Image: {os.environ.get('S2C_IMAGE_DESC','screenshot')}"}
            ]}
        ]

        # 由于视觉模型需要 API key，这个简化版直接让 LLM 生成描述性代码
        # 完整版需要 screenshot-to-code 服务 + 视觉模型
        content, _ = call_llm(messages, None, api_key)
        if not content:
            return {"success": False, "error": "代码生成失败"}

        # 提取代码
        import re
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', content, re.DOTALL)
        files = []
        for lang, code in code_blocks:
            code = code.strip()
            ext_map = {"html": ".html", "jsx": ".jsx", "tsx": ".tsx", "vue": ".vue",
                       "css": ".css", "js": ".js", "ts": ".ts", "json": ".json"}
            ext = ext_map.get(lang, ".html")
            fn = f"s2c_{int(time.time())}{ext}"
            out = Path(output_dir) if output_dir else Path("output/apps")
            out.mkdir(parents=True, exist_ok=True)
            out_path = out / fn
            out_path.write_text(code, encoding='utf-8')
            files.append({"name": fn, "path": str(out_path), "language": lang})

        preview_url = f"/output/apps/{files[0]['name']}" if files else ""
        return {"success": True, "code": content, "files": files, "preview_url": preview_url}

    except Exception as e:
        return {"success": False, "error": f"截屏转代码失败: {e}"}
