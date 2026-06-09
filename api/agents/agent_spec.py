"""智能体 — Spec-Kit 规格驱动开发（GitHub官方SDD）"""
import os, json, time, re, asyncio
from pathlib import Path

def run_spec_driven(msg, key, BASE, OUT, _LAST, _GENERATED_TOOLS):
    """Spec-Kit 流程：规格→规划→执行→验收"""
    from api.agent_llm import call_llm
    from api.agent_tools import exec_tool
    
    # 1. 生成规格（Spec）
    safe_name = re.sub(r'[^\\w\\u4e00-\\u9fff]', '_', msg[:30]).strip('_') or 'project'
    spec_prompt = f"""你是系统架构师。为以下需求生成完整规格文档。

需求：{msg[:300]}

请按以下格式输出（保存到 specs/{safe_name}.md）：
## 需求规格
- 功能点1
- 功能点2
...

## 技术规划
- 文件1：功能描述
- 文件2：功能描述
...

## 验收标准
- 标准1
- 标准2
...

只输出规格内容，不要解释。"""
    
    spec_msgs = [
        {"role": "system", "content": "你是Spec-Kit架构师，严格按格式输出规格。"},
        {"role": "user", "content": spec_prompt}
    ]
    spec_content, _ = call_llm(spec_msgs, None, key)
    
    if not spec_content or len(spec_content.strip()) < 50:
        return None  # 降级到普通流程
    
    # 保存规格文件
    safe_name = re.sub(r'[^\\w\\u4e00-\\u9fff]', '_', msg[:30]).strip('_')
    spec_dir = BASE / "specs"; spec_dir.mkdir(exist_ok=True)
    spec_path = spec_dir / f"{safe_name}.md"
    spec_path.write_text(f"# 规格：{msg[:50]}\n\n{spec_content}", encoding='utf-8')
    
    # 2. 按规格生成代码
    code_prompt = f"""你是高级开发者。严格按照以下规格生成代码。

规格文档：
{spec_content[:1000]}

要求：
1. 每个规划的文件都要生成
2. 代码必须完整可运行
3. 通过所有验收标准

请生成主要HTML文件（用file_write工具保存）。"""
    
    code_msgs = [
        {"role": "system", "content": "你是Spec-Kit开发者，严格按规格实现代码。"},
        {"role": "user", "content": code_prompt}
    ]
    code_result, tool_calls = call_llm(code_msgs, get_spec_tools(), key)
    
    # 执行工具调用
    if tool_calls:
        for tc in tool_calls:
            func = tc.get("function", {})
            args = {}
            try: args = json.loads(func.get("arguments", "{}"))
            except Exception:
                pass
            result = exec_tool(func.get("name", ""), args, BASE, OUT, _LAST, _GENERATED_TOOLS)
            if result.get("ok") and result.get("data"):
                return {"success": True, "result": result['data'], "mode": "spec", "spec": str(spec_path)}
    
    # 3. 验收检查
    if code_result and '/output/' in code_result:
        check_prompt = f"""你是QA工程师。检查以下代码是否满足规格。

规格：{spec_content[:500]}
代码：{code_result[:500]}

请输出：通过/不通过 + 原因清单"""
        check_msgs = [
            {"role": "system", "content": "你是严格的QA，只输出通过或不通过。"},
            {"role": "user", "content": check_prompt}
        ]
        check_result, _ = call_llm(check_msgs, None, key)
        
        if check_result and "不通过" in check_result[:15]:
            # 按验收反馈修复
            fix_prompt = f"验收未通过：{check_result[:200]}\n\n请修复代码并重新生成。"
            fix_msgs = [{"role": "user", "content": fix_prompt}]
            fix_result, _ = call_llm(fix_msgs, get_spec_tools(), key)
            if fix_result and '/output/' in fix_result:
                return {"success": True, "result": fix_result, "mode": "spec_fixed", "spec": str(spec_path)}
        
        return {"success": True, "result": code_result, "mode": "spec", "spec": str(spec_path)}
    
    return None  # 降级

def get_spec_tools():
    """Spec-Kit工具：file_write + search_modules"""
    return [
        {
            "type": "function",
            "function": {
                "name": "file_write",
                "description": "按规格保存文件",
                "parameters": {"type": "object", "properties": {
                    "name": {"type": "string", "description": "文件名"},
                    "content": {"type": "string", "description": "文件内容"},
                    "type": {"type": "string", "description": "文件类型"}
                }, "required": ["name", "content"]}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_modules",
                "description": "搜索相关模块",
                "parameters": {"type": "object", "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"}
                }, "required": ["keyword"]}
            }
        }
    ]
