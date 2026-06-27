"""数学计算技能 — 安全表达式求值"""
import math, ast, operator

skill_def = {
    "name": "math-calculator", "version": "1.0.0",
    "description": "数学表达式计算（安全沙箱）",
    "author": "AUTO-EVO-AI", "category": "工具", "icon": "🧮",
    "tags": ["数学", "计算", "表达式"],
    "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}}},
    "output_schema": {"type": "object", "properties": {"result": {"type": "number"}, "formula": {"type": "string"}}}
}

_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
}

def _safe_eval(expr):
    node = ast.parse(expr.strip(), mode='eval').body
    def _eval(n):
        if isinstance(n, ast.Constant): return n.value
        elif isinstance(n, ast.BinOp):
            op = _ALLOWED_OPS.get(type(n.op))
            if not op: raise ValueError(f"不支持的操作：{type(n.op).__name__}")
            return op(_eval(n.left), _eval(n.right))
        elif isinstance(n, ast.UnaryOp):
            op = _ALLOWED_OPS.get(type(n.op))
            if not op: raise ValueError(f"不支持的操作：{type(n.op).__name__}")
            return op(_eval(n.operand))
        elif isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name) and n.func.id in ('abs','round','int','float','sqrt','sin','cos','tan','log','log10','exp','pi','e'):
                args = [_eval(a) for a in n.args]
                fn = getattr(math, n.func.id, None) or {'pi': math.pi, 'e': math.e}.get(n.func.id)
                if callable(fn): return fn(*args)
                return fn
            raise ValueError(f"不支持的函数：{n.func.id}")
        raise ValueError(f"不支持的表达式：{type(n).__name__}")
    return _eval(node)

def execute(params, context=None):
    expr = params.get("expression", "")
    if not expr:
        return {"result": 0, "formula": "", "error": "请提供数学表达式（expression）"}
    try:
        result = _safe_eval(expr)
        return {"result": result, "formula": expr}
    except Exception as e:
        return {"result": 0, "formula": expr, "error": f"计算失败：{e}"}
