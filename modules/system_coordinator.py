# -*- coding: utf-8 -*-
"""AUTO-EVO-AI V0.1 - System Coordinator (v2→v3 Bridge)

此模块是 system_coordinator_v3.py 的向后兼容桥接。
所有核心功能由 SystemCoordinatorV3 实现（3981行）。
v2 原有的指标适配器（counter/increment/histogram/gauge）已在 EnterpriseModule 基类中提供。

迁移说明：
  - SystemCoordinatorV3 提供全部协调功能
  - _MetricsAdapter 功能 → modules/_base/enterprise_module.py / metrics.py
  - build_module_index → core/registry.py
  - register_module → core/module_manager.py
"""

__module_meta__ = {
    "id": "system-coordinator",
    "name": "System Coordinator (Bridge)",
    "version": "V0.1",
    "group": "system",
    "grade": "A",
    "tags": ["system", "coordinator", "bridge"],
    "description": "V2→V3 向后兼容桥接"
}

import logging
from modules.system_coordinator_v3 import SystemCoordinatorV3, SystemCoordinatorV3Analyzer

logger = logging.getLogger("evo.system-coordinator")

# 保持 v2 类名向后兼容
SystemCoordinator = SystemCoordinatorV3

# 兼容旧的模块导出
module_class = SystemCoordinatorV3
