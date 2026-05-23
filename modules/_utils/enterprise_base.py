# -*- coding: utf-8 -*-
"""
modules.enterprise_base — 兼容桥接
==================================
将 `from modules.enterprise_base import` 导入重定向到 `modules._base.enterprise_module`。
"""

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus

__all__ = ["EnterpriseModule", "ModuleStatus"]
