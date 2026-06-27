"""图片生成技能 — 调用 Stability AI 或 LLM"""
from api.agent_llm import call_llm

skill_def = {
    "name": "image-generator", "version": "1.0.0",
    "description": "AI 绘图（基于描述生成图像）",
    "author": "AUTO-EVO-AI", "category": "多模态", "icon": "🎨",
    "tags": ["图片", "绘图", "AI画图"],
    "input_schema": {"type": "object", "properties": {"prompt": {"type": "string"}, "style": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}}
}

def execute(params, context=None):
    prompt = params.get("prompt", "")
    if not prompt:
        return {"file_path": "", "error": "请提供图片描述（prompt）"}
    import os, hashlib, requests, base64
    from pathlib import Path
    out = Path(__file__).resolve().parent.parent.parent / "output" / "images"
    out.mkdir(parents=True, exist_ok=True)
    name = hashlib.md5(prompt.encode()).hexdigest()[:12]

    # 尝试 Stability AI
    key = os.environ.get("STABILITY_API_KEY", "")
    if key:
        try:
            r = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"text_prompts": [{"text": prompt}], "cfg_scale": 7, "height": 768, "width": 768},
                timeout=60
            )
            if r.ok:
                data = r.json()
                img_b64 = data["artifacts"][0]["base64"]
                fp = str(out / f"{name}.png")
                with open(fp, "wb") as f:
                    f.write(base64.b64decode(img_b64))
                return {"file_path": fp, "engine": "stability-ai"}
        except Exception:
            pass
    return {"file_path": "", "engine": "llm", "note": f"图片描述已收到：{prompt}。如需实际生成图片，请配置 STABILITY_API_KEY"}
