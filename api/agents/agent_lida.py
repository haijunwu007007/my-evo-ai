"""LIDA — 微软开源 LLM 驱动的自动可视化/数据分析工具"""
import os, json
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def lida_visualize(data_description: str = "", goal: str = "", chart_type: str = "") -> dict:
    """根据数据描述生成图表"""
    try:
        from lida import Manager, TextGenerationConfig
    except ImportError:
        return {"success": False, "error": "lida 未安装。运行: pip install lida"}
    if not data_description or not goal:
        return {"success": False, "error": "请提供 data_description 和 goal"}
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "需要 OPENAI_API_KEY"}
    try:
        mgr = Manager()
        tgc = TextGenerationConfig(n=1, temperature=0.2, model="gpt-4o", api_key=api_key)
        charts = mgr.visualize(goal=goal, data_description=data_description, textgen_config=tgc, library="matplotlib")
        results = [c.to_dict() if hasattr(c, "to_dict") else str(c) for c in charts]
        if chart_type:
            results = [r for r in results if isinstance(r, dict) and r.get("chart_type") == chart_type]
        return {"success": True, "charts": results, "total": len(results)}
    except Exception as e:
        return {"success": False, "error": f"可视化失败: {e}"}

def lida_explore(data_file_path: str = "", visualization_count: int = 3) -> dict:
    """探索性数据分析+自动出图"""
    try:
        from lida import Manager, TextGenerationConfig
    except ImportError:
        return {"success": False, "error": "lida 未安装"}
    if not data_file_path or not os.path.isfile(data_file_path):
        return {"success": False, "error": "文件不存在"}
    api_key = os.environ.get("OPENAI_API_KEY", "")
    try:
        mgr = Manager()
        tgc = TextGenerationConfig(n=1, temperature=0.2, model="gpt-4o", api_key=api_key)
        summary = mgr.summarize(file=data_file_path, textgen_config=tgc)
        goals = summary.goals if hasattr(summary, "goals") else [f"探索分析第{i+1}个角度" for i in range(visualization_count)]
        charts = []
        for g in goals[:visualization_count]:
            c = mgr.visualize(goal=str(g), data_description=str(summary), textgen_config=tgc)
            charts.extend(c)
        return {"success": True, "summary": str(summary)[:500], "charts_count": len(charts)}
    except Exception as e:
        return {"success": False, "error": f"探索分析失败: {e}"}

def lida_summarize(data_file_path: str = "") -> dict:
    """自动生成数据摘要"""
    try:
        from lida import Manager, TextGenerationConfig
    except ImportError:
        return {"success": False, "error": "lida 未安装"}
    if not data_file_path or not os.path.isfile(data_file_path):
        return {"success": False, "error": "文件不存在"}
    api_key = os.environ.get("OPENAI_API_KEY", "")
    try:
        mgr = Manager()
        tgc = TextGenerationConfig(n=1, temperature=0.2, model="gpt-4o", api_key=api_key)
        summary = mgr.summarize(file=data_file_path, textgen_config=tgc)
        return {"success": True, "summary": str(summary)[:1000], "fields": str(summary.fields if hasattr(summary, "fields") else [])[:500]}
    except Exception as e:
        return {"success": False, "error": f"摘要失败: {e}"}
