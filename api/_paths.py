from __future__ import annotations
"""
AUTO-EVO-AI V0.1 — 共享路径定义
=================================
替代 api_server.py 和 api/infra.py 中重复的 frozen detection + sys.path.insert
"""

import sys
from pathlib import Path

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
    _ORIGINAL_BASE = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    _ORIGINAL_BASE = BASE_DIR

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "modules"))
