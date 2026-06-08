"""AUTO-EVO-AI 智能体单元测试"""
import sys, json
sys.path.insert(0, "api")
try:
    from agent_core import _match_modules, _eval_modules
    print("✅ agent_core 导入成功")
    print(f"✅ 模块评估: {_eval_modules()}")
    print(f"✅ 匹配'报名': {_match_modules('开发一个报名系统')[:3]}")
    print(f"✅ 匹配'监控': {_match_modules('系统监控报警')[:3]}")
    print(f"✅ 匹配'搜索': {_match_modules('搜索引擎优化')[:3]}")
except Exception as e:
    print(f"❌ 导入失败: {e}")

try:
    from agent_llm import call_llm, _LLM_PROVIDERS
    print(f"✅ LLM导入成功, {len(_LLM_PROVIDERS)}个Provider")
except Exception as e:
    print(f"❌ LLM导入失败: {e}")

try:
    from agent_tools import exec_tool
    print("✅ 工具模块导入成功")
except Exception as e:
    print(f"❌ 工具模块导入失败: {e}")
