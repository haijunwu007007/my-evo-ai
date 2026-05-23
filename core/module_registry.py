"""
模块注册表+依赖解析引擎 — 570 模块输入输出自动匹配
"""
import os, ast, json, logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ModuleRegistry:
    def __init__(self):
        self._modules: Dict[str, dict] = {}
        self._deps: Dict[str, List[str]] = {}
        self._reverse_deps: Dict[str, List[str]] = {}

    def scan(self, modules_dir: str) -> dict:
        """扫描模块目录，解析每个模块的输入输出"""
        count = 0
        for f in sorted(os.listdir(modules_dir)):
            if not f.endswith('.py') or f.startswith('__'):
                continue
            path = os.path.join(modules_dir, f)
            name = f.replace('.py', '')
            info = self._parse_module(path, name)
            self._modules[name] = info
            count += 1

        return {
            "total": count,
            "with_inputs": sum(1 for m in self._modules.values() if m.get("inputs")),
            "with_outputs": sum(1 for m in self._modules.values() if m.get("outputs")),
        }

    def _parse_module(self, path: str, name: str) -> dict:
        """AST 解析单个模块"""
        try:
            src = open(path, encoding='utf-8').read()
            tree = ast.parse(src)

            def _str_val(node):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    return node.value
                _old_str_type = getattr(ast, 'Str', None)
                if _old_str_type and isinstance(node, _old_str_type):
                    return node.s
                return str(node)

            inputs, outputs = [], []
            for node in ast.walk(tree):
                if isinstance(node, ast.Dict):
                    for k, v in zip(node.keys, node.values):
                        kn = _str_val(k) if k else None
                        if kn == 'inputs':
                            if isinstance(v, ast.List):
                                inputs = [_str_val(e) for e in v.elts]
                            elif isinstance(v, ast.Dict):
                                inputs = [_str_val(k2) for k2 in v.keys if k2]
                        if kn == 'outputs':
                            if isinstance(v, ast.List):
                                outputs = [_str_val(e) for e in v.elts]
                            elif isinstance(v, ast.Dict):
                                outputs = [_str_val(k2) for k2 in v.keys if k2]

            # Fallback: scan for execute params
            has_execute = any(
                isinstance(n, ast.FunctionDef) and n.name == 'execute'
                for n in ast.walk(tree)
            )
            if not inputs:
                for n in ast.walk(tree):
                    if isinstance(n, ast.FunctionDef) and n.name == 'execute':
                        inputs = [a.arg for a in n.args.args if a.arg != 'self']
                        break

            lines = src.strip().split('\n')
            return {
                "name": name,
                "inputs": inputs or [],
                "outputs": outputs or ["success", "data"],
                "has_execute": has_execute,
                "lines": len(lines),
                "path": path,
            }
        except Exception as e:
            logger.warning("[REGISTRY] parse error %s: %s", name, e)
            return {"name": name, "inputs": [], "outputs": [], "has_execute": False, "lines": 0, "path": path}

    def build_deps(self):
        """构建模块依赖图：如果 A 的输出匹配 B 的输入，则 A→B"""
        self._deps = {}
        self._reverse_deps = {}

        for name, info in self._modules.items():
            deps = []
            for other_name, other_info in self._modules.items():
                if name == other_name:
                    continue
                # Check if info's outputs match other's inputs
                out_set = set(info.get("outputs", []))
                in_set = set(other_info.get("inputs", []))
                if out_set & in_set:
                    deps.append(other_name)
            self._deps[name] = deps

        # Build reverse deps
        for name, deps in self._deps.items():
            for dep in deps:
                if dep not in self._reverse_deps:
                    self._reverse_deps[dep] = []
                self._reverse_deps[dep].append(name)

    def resolve_chain(self, start: str, target_output: str = "") -> List[str]:
        """解析从 start 模块开始的可执行链"""
        if start not in self._modules:
            return []

        visited = set()
        chain = []

        def dfs(name):
            if name in visited:
                return
            visited.add(name)
            chain.append(name)
            for dep in self._deps.get(name, []):
                if dep not in visited:
                    dfs(dep)

        dfs(start)
        return chain

    def match_modules(self, output_key: str) -> List[str]:
        """根据输出键找到能消费它的模块"""
        return [
            name for name, info in self._modules.items()
            if output_key in info.get("inputs", [])
        ]

    def get_chain_info(self, start: str) -> dict:
        chain = self.resolve_chain(start)
        return {
            "start": start,
            "chain": chain,
            "length": len(chain),
            "modules": [self._modules.get(m, {}) for m in chain],
        }


_registry = None

def get_registry() -> ModuleRegistry:
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry


def scan_and_build(modules_dir: str) -> dict:
    """一键扫描+构建依赖"""
    reg = get_registry()
    result = reg.scan(modules_dir)
    reg.build_deps()
    top_matches = sum(1 for v in reg._modules.values() if v.get("has_execute"))
    return {
        **result,
        "dependencies": len(reg._deps),
        "reachable": top_matches,
    }
