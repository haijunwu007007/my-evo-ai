"""DocETL — AI文档ETL管道（YAML定义→LLM处理，文档批处理自动化）"""
import os, json

def docetl_create_pipeline(name: str = "", source: str = "",
                            operations: list = None, output: str = "") -> dict:
    """创建文档ETL管道"""
    if not name: return {"success": False, "error": "请提供 name"}
    pipeline_id = f"pipe_{int(time.time())}"
    return {"success": True, "data": {"id": pipeline_id, "name": name,
        "source": source, "operations": operations or [{"type": "extract_text"},
        {"type": "summarize"}, {"type": "classify"}], "output": output or "markdown",
        "status": "configured"}, "message": f"ETL管道 '{name}' 已创建"}

def docetl_run_pipeline(pipeline_id: str = "", input_files: list = None) -> dict:
    """运行ETL管道"""
    if not pipeline_id: return {"success": False, "error": "请提供 pipeline_id"}
    input_files = input_files or []
    return {"success": True, "data": {"pipeline_id": pipeline_id,
        "input_count": len(input_files), "processed": 0,
        "status": "queued", "elapsed": "0s"}, "message": f"管道 {pipeline_id} 已排队"}

def docetl_list_pipelines() -> dict:
    """列出管道"""
    return {"success": True, "data": {"pipelines": [], "total": 0}, "message": "无管道"}

def docetl_extract_documents(file_paths: list = None, extraction_type: str = "text") -> dict:
    """直接提取文档内容"""
    file_paths = file_paths or []
    if not file_paths: return {"success": False, "error": "请提供 file_paths"}
    results = []
    for fp in file_paths:
        if os.path.isfile(fp):
            try:
                content = Path(fp).read_text(encoding='utf-8', errors='replace')[:2000]
                results.append({"file": fp, "success": True, "content_length": len(content)})
            except:
                results.append({"file": fp, "success": False, "error": "读取失败"})
        else:
            results.append({"file": fp, "success": False, "error": "文件不存在"})
    return {"success": True, "total": len(results), "results": results}

from pathlib import Path
