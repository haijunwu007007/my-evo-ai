"""AgentEval — Agent性能评估与基准测试"""
import os, json, time
from pathlib import Path

def agenteval_benchmark(agent_type: str = "chat", test_cases: list = None,
                        metrics: list = None) -> dict:
    """评测Agent性能
    Args:
        agent_type: Agent类型 (chat/dev/research/codegen)
        test_cases: 自定义测试用例列表
        metrics: 评测指标列表 (accuracy/response_time/coverage/relevance)
    Returns:
        {"success": bool, "scores": dict, "details": list}
    """
    if not test_cases:
        # 默认测试用例
        test_cases = [
            {"id": "tc_01", "input": "写一个待办事项HTML应用", "expected": "包含增删改", "category": "code"},
            {"id": "tc_02", "input": "搜索Python最新动态", "expected": "返回搜索结果的摘要", "category": "research"},
            {"id": "tc_03", "input": "画一只猫", "expected": "返回图片", "category": "creative"},
            {"id": "tc_04", "input": "系统有多少模块", "expected": "模块数量统计", "category": "info"},
            {"id": "tc_05", "input": "你好，帮我介绍一下自己", "expected": "友好回复", "category": "chat"},
        ]
    if not metrics:
        metrics = ["accuracy", "response_time", "relevance"]

    api_key = os.environ.get("OPENAI_API_KEY", "")
    results = []

    for tc in test_cases:
        start = time.time()
        try:
            from api.agent_llm import call_llm
            from api.agent_tools import exec_tool
            BASE = Path(__file__).resolve().parent.parent
            OUT = BASE / "output"
            TOOLS_DIR = OUT / "tools"
            _GENERATED = {}
            _LAST = {}

            # 判断是否需要工具
            code_keywords = ["写", "创建", "开发", "实现", "生成"]
            research_keywords = ["搜索", "查", "研究", "分析"]
            info_keywords = ["多少", "统计", "状态", "怎么样"]

            needs_tool = False
            for kw in code_keywords + research_keywords + info_keywords:
                if kw in tc["input"]:
                    needs_tool = True
                    break

            if needs_tool:
                msgs = [{"role": "system", "content": "你是一个AI助手，使用可用工具回答问题。"},
                       {"role": "user", "content": tc["input"]}]
                # 走工具循环
                from api.agent_core import create_engine
                process = create_engine(BASE, OUT, TOOLS_DIR, BASE / "data" / "mem.db")
                result = process(tc["input"], key=api_key)
            else:
                msgs = [{"role": "system", "content": "你是一个友好的AI助手。"},
                       {"role": "user", "content": tc["input"]}]
                content, _ = call_llm(msgs, None, api_key)
                result = {"success": True, "result": content, "mode": "direct"}

            elapsed = time.time() - start
            passed = bool(result and result.get("success"))
            results.append({
                "id": tc["id"],
                "input": tc["input"][:50],
                "expected": tc["expected"],
                "passed": passed,
                "response_time_s": round(elapsed, 2),
                "response": str(result.get("result", ""))[:200]
            })
        except Exception as e:
            results.append({
                "id": tc["id"],
                "input": tc["input"][:50],
                "passed": False,
                "response_time_s": round(time.time() - start, 2),
                "error": str(e)
            })

    passed_count = sum(1 for r in results if r.get("passed"))
    avg_time = sum(r.get("response_time_s", 0) for r in results) / max(len(results), 1)

    return {
        "success": True,
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "pass_rate": f"{passed_count/len(results)*100:.1f}%",
            "avg_response_time_s": round(avg_time, 2)
        },
        "results": results,
        "recommendation": "需要优化" if passed_count < len(results) * 0.8 else "通过"
    }
