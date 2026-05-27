"""Strip agent_orchestrator.py to just ModuleRegistry + AgentOrchestrator"""
import os, ast

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with open("modules/agent_orchestrator.py", encoding="utf-8") as f:
    lines = f.readlines()

# Keep: header(0-54) + ModuleRegistry(581-931) + AgentOrchestrator(1432-end)
keep = []
keep.extend(lines[:55])  # header + module_meta
keep.append("\n")
keep.append("import re, time, uuid, json, logging, threading\n")
keep.append("from datetime import datetime\n")
keep.append("from typing import Any, Dict, List, Optional, Callable, Tuple, Set\n")
keep.append("from collections import defaultdict, deque\n")
keep.append("from concurrent.futures import ThreadPoolExecutor, as_completed\n")
keep.append("from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin\n")
keep.append("from modules._base.metrics import prometheus_timer, metrics_collector\n")
keep.append("from modules._base.orchestrator_types import TaskStatus, TaskPriority, IntentCategory\n")
keep.append("from modules._base.orchestrator_types import ModuleCapability, SubTask, OrchestratorTask\n")
keep.append("from modules._base.orchestrator_intent import AIIntentAnalyzer, IntentAnalyzer\n")
keep.append("from modules._base.orchestrator_execution import TaskPlanner, ModuleExecutor, EvolutionFeedback, ExecutionDAGBuilder\n")
keep.append("\n")
keep.append("logger = logging.getLogger(__name__)\n")
keep.append("\n")

# ModuleRegistry (581-931) - 0-indexed
keep.extend(lines[581:932])
keep.append("\n")

# AgentOrchestrator (1432-end) - 0-indexed
keep.extend(lines[1432:])

with open("modules/agent_orchestrator.py", "w", encoding="utf-8") as f:
    f.writelines(keep)

print(f"Rewritten: {len(keep)} lines ({sum(len(l) for l in keep)//1024}KB)")
print(f"Kept: header+L0-54 + ModuleRegistry(L582-931) + AgentOrchestrator(L1433-end)")
print(f"Extracted to _base/: types(6 classes) + intent(2 classes) + execution(4 classes)")
