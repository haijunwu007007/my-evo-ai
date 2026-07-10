"""GPT-Pilot — 全栈AI开发者（需求→代码→调试全流程）"""
import logging
logger = logging.getLogger("evo.agent_gptpilot")

import os, json, time
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def gptpilot_build(description: str = "", tech_stack: str = "fastapi+vue",
                   output_dir: str = "", debug: bool = True) -> dict:
    """从需求生成完整项目
    Args:
        description: 项目描述
        tech_stack: 技术栈 (fastapi+vue / django+react / flask+html / fullstack)
        output_dir: 输出目录
        debug: 是否自动调试修复
    Returns:
        {"success": bool, "project_dir": str, "files": list, "summary": str}
    """
    try:
        # 尝试使用 gpt-pilot
        try:
            from gpt_pilot import Pilot
            pilot = Pilot()
            result = pilot.create_project(
                description=description,
                tech_stack=tech_stack,
                output_dir=output_dir or "generated_projects"
            )
            return {
                "success": True,
                "project_dir": result.get("project_dir", ""),
                "files": result.get("files", []),
                "summary": result.get("summary", "")
            }
        except ImportError:
            # 回退：系统自带的并发开发流程
            from api.agent_llm import call_llm
            api_key = os.environ.get("OPENAI_API_KEY", "")

            out_dir = Path(output_dir) if output_dir else Path("output/projects") / f"project_{int(time.time())}"
            out_dir.mkdir(parents=True, exist_ok=True)

            # 1. 生成需求规格
            spec_msgs = [
                {"role": "system", "content": "你是一个软件架构师。输出项目结构和规格。"},
                {"role": "user", "content": f"项目: {description}\n技术栈: {tech_stack}\n输出JSON: {{'project_name':'','structure':[{{'path':'','desc':''}}],'spec':''}}"}
            ]
            spec, _ = call_llm(spec_msgs, None, api_key)
            spec_file = out_dir / "SPEC.md"
            spec_file.write_text(spec or description, encoding='utf-8')

            # 2. 生成代码文件
            import concurrent.futures
            gen_files = []

            def _gen_file(path, desc):
                prompt = f"生成文件 {path}。项目: {description}\n描述: {desc}\n技术栈: {tech_stack}\n输出完整代码。"
                msgs = [{"role": "system", "content": f"生成 {path} 的完整代码。"},
                       {"role": "user", "content": prompt}]
                code, _ = call_llm(msgs, None, api_key)
                if code:
                    fp = out_dir / path
                    fp.parent.mkdir(parents=True, exist_ok=True)
                    # 提取代码块
                    import re
                    blocks = re.findall(r'```\w*\n(.*?)```', code, re.DOTALL)
                    final_code = blocks[0] if blocks else code
                    fp.write_text(final_code.strip(), encoding='utf-8')
                    return {"path": path, "size": len(final_code)}

            # 默认结构
            structure = [
                {"path": "backend/main.py", "desc": "FastAPI后端主文件"},
                {"path": "backend/requirements.txt", "desc": "Python依赖"},
                {"path": "frontend/index.html", "desc": "前端页面"},
            ]

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(_gen_file, s["path"], s["desc"]): s for s in structure}
                for f in concurrent.futures.as_completed(futures):
                    try:
                        r = f.result()
                        if r: gen_files.append(r)
                    except Exception as _e:
                        logger.warning(f"error: {_e}")

            return {
                "success": True,
                "project_dir": str(out_dir),
                "files": gen_files,
                "summary": f"项目 {out_dir.name} 已生成，共 {len(gen_files)} 个文件"
            }

    except Exception as e:
        return {"success": False, "error": f"GPT-Pilot 构建失败: {e}"}
