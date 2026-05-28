"""将 system_coordinator_v3.py 3951行拆分为包"""
import re

SRC = "D:/AUTO-EVO-AI-V0.1/modules/system_coordinator_v3.py"
DST = "D:/AUTO-EVO-AI-V0.1/modules/system_coordinator_v3"

with open(SRC, encoding="utf-8") as f:
    content = f.read()

# 找到所有类/函数起始位置
sections = []
for m in re.finditer(r'^(?:class |def create_coordinator)', content, re.MULTILINE):
    sections.append(m.start())
sections.append(len(content))

# 提取每个类的内容
class_blocks = {}
for i in range(len(sections) - 1):
    block = content[sections[i]:sections[i+1]]
    first_line = block.split('\n')[0]
    m = re.match(r'(?:class |def )(\w+)', first_line)
    if m:
        class_blocks[m.group(1)] = block

# 类名→文件名映射
FILE_MAP = {
    "SystemCoordinatorV3Analyzer": "analyzer.py",
    "ModuleCapabilityGraph": "graph.py",
    "AutonomousLoop": "loop.py",
    "CrossModuleOrchestrator": "orchestrator.py",
    "SystemCoordinatorV3": "coordinator.py",
    "create_coordinator_v3": "coordinator.py",
}

# 每个文件的头部（独立导入）
HEADERS = {
    "analyzer.py": (
        '# -*- coding: utf-8 -*-\n'
        '# 原 system_coordinator_v3.py L60-216 — 协调器分析器\n'
        '"""系统协调器分析器"""\n'
        'import logging, time, re\n'
        'from typing import Dict, Any, Optional, List\n'
        'from pathlib import Path\n'
        'from collections import defaultdict\n'
        'logger = logging.getLogger("evo.coordinator.v3")\n\n'
    ),
    "graph.py": (
        '# -*- coding: utf-8 -*-\n'
        '# 原 system_coordinator_v3.py L217-716 — 模块能力图谱\n'
        '"""模块能力图谱 — 自动扫描所有模块并构建能力索引"""\n'
        'import logging, time, re, os, sys, math, asyncio\n'
        'from typing import Dict, Any, Optional, List, Set, Callable\n'
        'from pathlib import Path\n'
        'from collections import defaultdict, Counter\n'
        'from datetime import datetime, timedelta\n'
        'from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin\n'
        'from modules._base.metrics import prometheus_timer, metrics_collector\n'
        'logger = logging.getLogger("evo.coordinator.v3")\n\n'
    ),
    "loop.py": (
        '# -*- coding: utf-8 -*-\n'
        '# 原 system_coordinator_v3.py L717-1209 — 自主决策循环\n'
        '"""自主决策循环"""\n'
        'import logging, time, re, os, sys, math, asyncio\n'
        'from typing import Dict, Any, Optional, List, Callable\n'
        'from pathlib import Path\n'
        'from collections import defaultdict\n'
        'from datetime import datetime, timedelta\n'
        'from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin\n'
        'logger = logging.getLogger("evo.coordinator.v3")\n\n'
    ),
    "orchestrator.py": (
        '# -*- coding: utf-8 -*-\n'
        '# 原 system_coordinator_v3.py L1210-3043 — 跨模块编排器\n'
        '"""跨模块编排器"""\n'
        'import logging, time, re, os, sys, math, asyncio\n'
        'import threading, importlib, inspect\n'
        'from typing import Dict, Any, Optional, List, Set, Callable\n'
        'from pathlib import Path\n'
        'from collections import defaultdict, Counter\n'
        'from datetime import datetime, timedelta\n'
        'from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin\n'
        'from modules._base.metrics import prometheus_timer, metrics_collector\n'
        'logger = logging.getLogger("evo.coordinator.v3")\n\n'
    ),
    "coordinator.py": (
        '# -*- coding: utf-8 -*-\n'
        '# 原 system_coordinator_v3.py L3044-3951 — 系统协调器主类+工厂\n'
        '"""系统协调器主类 + 工厂函数"""\n'
        'import logging, time, re, os, sys, math, asyncio\n'
        'import threading, importlib, inspect\n'
        'from typing import Dict, Any, Optional, List, Callable\n'
        'from pathlib import Path\n'
        'from collections import defaultdict, Counter\n'
        'from datetime import datetime, timedelta\n'
        'from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin\n'
        'from modules._base.metrics import prometheus_timer, metrics_collector\n'
        'from modules.system_coordinator_v3.analyzer import SystemCoordinatorV3Analyzer\n'
        'from modules.system_coordinator_v3.graph import ModuleCapabilityGraph\n'
        'from modules.system_coordinator_v3.loop import AutonomousLoop\n'
        'from modules.system_coordinator_v3.orchestrator import CrossModuleOrchestrator\n'
        'logger = logging.getLogger("evo.coordinator.v3")\n\n'
    ),
}

# 写入每个子文件
for class_name, filename in FILE_MAP.items():
    if class_name == "create_coordinator_v3":
        continue  # 附录在 coordinator.py 末尾
    block = class_blocks.get(class_name, "")
    if not block:
        print(f"  !! 未找到 {class_name}")
        continue

    filepath = f"{DST}/{filename}"
    header = HEADERS[filename]

    # 去掉 class 行之前的注释和装饰器
    lines = block.split('\n')
    # 找到 class/def 行
    for i, line in enumerate(lines):
        if line.strip().startswith(('class ', 'def ')):
            code = '\n'.join(lines[i:])
            break
    else:
        code = block

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(code)
        f.write('\n')
    print(f"  -> {filepath} (原{class_name})")

# 附加 create_coordinator_v3 到 coordinator.py
factory = class_blocks.get("create_coordinator_v3", "")
if factory:
    with open(f"{DST}/coordinator.py", "a", encoding="utf-8") as f:
        f.write('\n\n')
        f.write(factory)
    print(f"  -> [append] create_coordinator_v3 → coordinator.py")

# 原文件替换为 shim
shim_lines = [
    '# -*- coding: utf-8 -*-',
    '# !! 此文件已拆分为 system_coordinator_v3/ 包，保留为 re-export shim',
    '"""AUTO-EVO-AI 系统核心协调器 v3.0 (已拆分)"""',
    '',
    'from modules.system_coordinator_v3 import (',
    '    SystemCoordinatorV3Analyzer,',
    '    ModuleCapabilityGraph,',
    '    AutonomousLoop,',
    '    CrossModuleOrchestrator,',
    '    SystemCoordinatorV3,',
    '    create_coordinator_v3,',
    ')',
    '',
]
with open(SRC, "w", encoding="utf-8") as f:
    f.write('\n'.join(shim_lines) + '\n')
print(f"\n  -> {SRC} → 已替换为 {len(shim_lines)} 行 re-export shim")
print("\n拆分完成！")
