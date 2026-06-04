"""system_coordinator_v3 包 — 拆分为6个子模块"""
import logging
_logger = logging.getLogger("evo.coordinator.v3")

try:
    from modules.system_coordinator_v3.analyzer import SystemCoordinatorV3Analyzer
except Exception as _e:
    _logger.warning(f"[v3] analyzer 导入失败: {_e}")
    SystemCoordinatorV3Analyzer = None

try:
    from modules.system_coordinator_v3.graph import ModuleCapabilityGraph
except Exception as _e:
    _logger.warning(f"[v3] graph 导入失败: {_e}")
    ModuleCapabilityGraph = None

try:
    from modules.system_coordinator_v3.loop import AutonomousLoop
except Exception as _e:
    _logger.warning(f"[v3] loop 导入失败: {_e}")
    AutonomousLoop = None

try:
    from modules.system_coordinator_v3.orchestrator import CrossModuleOrchestrator
except Exception as _e:
    _logger.warning(f"[v3] orchestrator 导入失败: {_e}")
    CrossModuleOrchestrator = None

try:
    from modules.system_coordinator_v3.coordinator import SystemCoordinatorV3, create_coordinator_v3
except Exception as _e:
    _logger.warning(f"[v3] coordinator 导入失败: {_e}")
    SystemCoordinatorV3 = None
    create_coordinator_v3 = None
