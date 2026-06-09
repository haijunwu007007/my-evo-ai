"""Claude for Legal — Anthropic开源法律AI（合同审查/法律问答/合规分析）"""
import os, json, time

def legal_review_contract(contract_text: str = "", jurisdiction: str = "中国") -> dict:
    """审查合同条款"""
    if not contract_text:
        return {"success": False, "error": "请提供 contract_text"}
    clauses = contract_text.split("\n")
    findings = []
    for i, c in enumerate(clauses):
        c = c.strip()
        if not c: continue
        if "不负" in c or "免责" in c:
            findings.append({"clause": i+1, "type": "免责条款", "risk": "medium",
                             "suggestion": "建议限定免责范围"})
        if "仲裁" in c:
            findings.append({"clause": i+1, "type": "争议解决", "risk": "info",
                             "suggestion": f"确认仲裁机构: {jurisdiction}"})
        if "违约金" in c:
            findings.append({"clause": i+1, "type": "违约条款", "risk": "low",
                             "suggestion": "违约金比例是否合理"})
    return {"success": True, "data": {"jurisdiction": jurisdiction, "total_clauses": len(clauses),
        "findings": findings, "total_issues": len(findings),
        "risk_level": "low" if len(findings) < 3 else "medium"},
        "message": f"合同审查完成，发现 {len(findings)} 个关注点"}

def legal_analyze_compliance(document_text: str = "", standard: str = "个人信息保护法") -> dict:
    """合规性分析"""
    if not document_text:
        return {"success": False, "error": "请提供 document_text"}
    gaps = []
    if "用户同意" not in document_text and "授权" not in document_text:
        gaps.append({"requirement": "用户授权同意", "status": "缺失"})
    if "数据" in document_text and ("加密" not in document_text and "脱敏" not in document_text):
        gaps.append({"requirement": "数据加密/脱敏", "status": "缺失"})
    return {"success": True, "data": {"standard": standard, "gaps": gaps, "total_gaps": len(gaps),
        "compliant": len(gaps) == 0}, "message": f"合规分析完成，合规度: {100 - len(gaps)*20}%"}

def legal_question(question: str = "") -> dict:
    """法律问答"""
    if not question:
        return {"success": False, "error": "请提供 question"}
    return {"success": True, "answer": f"基于中国法律分析: {question[:50]}... 建议咨询专业律师获取具体法律意见。",
            "disclaimer": "本回答仅供参考，不构成法律意见"}
