"""统一工具链 — 注册到 Evo 系统"""
import logging
logger = logging.getLogger("evo.unified")

import json
from api.agent_tools import _tools
from api.hub.unified_toolchain import TOOLS

for name, func in TOOLS.items():
    _tools[name] = func

logger.info(f"[unified] registered {len(TOOLS)} industry tools: {list(TOOLS.keys())}")
