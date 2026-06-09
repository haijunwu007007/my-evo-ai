"""智能体 — yoyo-evolve 自进化机制（自主阅读源码并改进）"""
import os, json, time, re, importlib
from pathlib import Path

def auto_evolve(BASE, memos=None):
    """自进化：读源码→分析→改进建议→测试→提交"""
    try:
        # 1. 读自己的源码
        core_path = BASE / "api" / "agent_core.py"
        if not core_path.exists(): return
        source = core_path.read_text(encoding='utf-8')
        
        # 2. 分析可改进点
        issues = []
        if len(source) > 5000:
            issues.append(f"文件过大({len(source)}字符)，建议拆分")
        if "try:" in source and "except Exception:
            pass" in source:
            count = source.count("except Exception:
            pass")
            if count > 5:
                issues.append(f"有{count}处空except，建议记录错误日志")
        
        # 3. 分析函数复杂度
        funcs = re.findall(r'def (\w+)\(', source)
        large_funcs = []
        for fname in funcs:
            m = re.search(rf'def {fname}\(.*?\):.*?(?=\ndef |\Z)', source, re.DOTALL)
            if m and len(m.group()) > 300:
                large_funcs.append(f"{fname}({len(m.group())}字符)")
        if large_funcs:
            issues.append(f"大函数: {'; '.join(large_funcs[:3])}")
        
        # 4. 检查重复代码模式
        patterns = set()
        for i in range(len(source) - 50):
            chunk = source[i:i+50]
            if source.count(chunk) > 2 and len(chunk) > 30:
                patterns.add(chunk[:20])
        dup_count = len(patterns)
        if dup_count > 3:
            issues.append(f"发现{dup_count}段重复代码模式，建议抽取为公共函数")
        
        # 5. 记录分析结果
        if memos and issues:
            memos.save_experience("代码自进化分析", f"发现{len(issues)}个问题: {'; '.join(issues[:5])}")
        
        return {"issues": issues, "funcs": funcs, "size": len(source)}
    except Exception as e:
        return {"error": str(e)}

def self_improve(BASE, target_file, direction=""):
    """自我改进：针对具体文件生成优化补丁"""
    fp = BASE / target_file
    if not fp.exists(): return {"success": False, "error": "文件不存在"}
    try:
        source = fp.read_text(encoding='utf-8')
        from api.agent_llm import call_llm
        prompt = f"""你是代码优化专家。分析以下代码，输出具体的优化建议。

文件：{target_file}
大小：{len(source)}字符
方向：{direction or '性能+可读性'}

代码：
{source[:2000]}

请输出具体的优化建议（格式：行号+建议+预期效果）"""
        msgs = [
            {"role": "system", "content": "你是代码优化专家，输出具体可执行的优化建议。"},
            {"role": "user", "content": prompt}
        ]
        suggestions, _ = call_llm(msgs, None, "")
        return {"success": True, "file": str(fp), "suggestions": suggestions[:1000] if suggestions else "无建议"}
    except Exception as e:
        return {"success": False, "error": str(e)}
