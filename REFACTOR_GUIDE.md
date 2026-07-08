# 大模块拆分建议
#
# 以下模块文件体积过大，建议拆分为子模块以提高可维护性：
#
# ┌──────────────────────────────────────────┬────────┬──────────────┐
# │ 文件路径                                 │ 大小   │ 建议拆分为   │
# ├──────────────────────────────────────────┼────────┼──────────────┤
# │ modules/agent_resource_control.py       │ 72KB   │ control/     │
# │ modules/system_coordinator_v3/orch...   │ 68KB   │ 已有子目录   │
# │ core/decision_engine.py                 │ 56KB   │ engine/      │
# │ modules/agent_planner.py                │ 55KB   │ planner/     │
# │ modules/m53_finance_data.py             │ 52KB   │ finance/     │
# │ core/llm_gateway.py                     │ 50KB   │ llm/         │
# │ modules/ragflow.py                      │ 50KB   │ rag/         │
# │ api/routes/routes_new_features.py       │ 49KB   │ features/    │
# │ modules/cli_interface.py                │ 49KB   │ cli/         │
# │ modules/second_brain.py                 │ 48KB   │ brain/       │
# └──────────────────────────────────────────┴────────┴──────────────┘
#
# 拆分方法：
#   1. 创建子目录（如 modules/control/）
#   2. 将功能拆分为多个文件（如 __init__.py + agent.py + resource.py）
#   3. 在 __init__.py 中暴露原有接口
#   4. 逐步迁移，保持向后兼容
