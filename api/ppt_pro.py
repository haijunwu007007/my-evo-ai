import logging
logger = logging.getLogger("evo.ppt_pro")
# AUTO-EVO-AI PPT专业工具
"""LLM驱动的PPT生成器"""
import os, json, time, httpx, re
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output"

def _llm_call(prompt: str, key: str) -> str:
    if key.startswith("sk-"):
        url = "https://api.deepseek.com/v1/chat/completions"
        model = "deepseek-chat"
    else:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        model = "glm-4-flash"
    payload = {"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":8192}
    r = httpx.post(url, headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}, json=payload, timeout=60)
    if r.status_code != 200: return ""
    return r.json()["choices"][0]["message"]["content"]

def generate_ppt(topic: str, slides: list, api_key: str) -> dict:
    key = api_key or os.environ.get("ZHIPU_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
    if not key: return {"ok":False,"data":"需要API Key"}
    try:
        sj = json.dumps(slides, ensure_ascii=False)
        prompt = f"""用python-pptx库生成专业PPT。主题:{topic}。每页:{sj}。
要求:深色主题(#1a1a2e背景+白色文字);标题36pt加粗;正文18pt;配色#4361ee/#f59e0b/#06d6a0;
每页添加形状装饰;文件保存到/tmp/ppt_output.pptx。只返回Python代码。"""
        code = _llm_call(prompt, key)
        if not code: return {"ok":False,"data":"LLM无响应"}
        code = code.replace("```python","").replace("```","").strip()
        code_path = str(OUT / f"ppt_gen_{int(time.time())}.py")
        Path(code_path).write_text(code, encoding='utf-8')
        import subprocess
        ppt_path = "/tmp/ppt_output.pptx"
        if os.path.exists(ppt_path): os.remove(ppt_path)
        r = subprocess.run(["python3",code_path], capture_output=True, text=True, timeout=60)
        if os.path.exists(ppt_path):
            import shutil
            fn = f"ppt_{int(time.time())}.pptx"
            shutil.copy2(ppt_path, str(OUT / fn))
            return {"ok":True,"data":f"✅ **{topic}PPT**\n[📄 下载](/output/{fn})"}
        return {"ok":False,"data":f"失败:\n{r.stderr[:500]}"}
    except Exception as e:
        return {"ok":False,"data":f"异常:{e}"}

def generate_slides_from_message(msg: str) -> list:
    topic = re.sub(r'(做|一份|的|介绍|PPT|ppt|演示文稿|演示|五页|六页|页|\d+)','',msg).strip() or "主题"
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ZHIPU_API_KEY") or ""
    if key:
        try:
            p = f"为'{topic}'生成6页PPT的标题和内容。返回JSON数组，每个元素有title和text。text写专业中文(50-100字)。只返回JSON。"
            content = _llm_call(p, key)
            if content:
                content = content.replace("```json","").replace("```","").strip()
                slides = json.loads(content)
                if isinstance(slides, list) and len(slides) >= 3: return slides
        except Exception as _e:
            logger.warning(f"error: {_e}")
    return [
        {"title":f"{topic}介绍","text":f"{topic}是一种专业的技术产品，下面从多维度进行全面介绍。"},
        {"title":"产品概述","text":f"{topic}凭借先进技术和可靠品质获得广泛认可。"},
        {"title":"核心特点","text":"• 优异性能表现\\n• 稳定可靠品质\\n• 节能环保设计\\n• 便捷安装维护"},
        {"title":"应用场景","text":"住宅建筑\\n商业楼宇\\n工业厂房\\n公共工程"},
        {"title":"技术优势","text":"采用国际先进技术，通过多项权威认证。"},
        {"title":"总结","text":f"{topic}将持续为客户创造价值，推动行业进步。"}
    ]
