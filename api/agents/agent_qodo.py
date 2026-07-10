"""Qodo-Cover — AI自动生成单元测试"""
import logging
logger = logging.getLogger("evo.agent_qodo")

import os, json
from pathlib import Path
import os
_DEFAULT_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
_LLM_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
_LLM_MODEL = "deepseek-chat"

def generate_tests(source_path: str = "", source_code: str = "", 
                   framework: str = "pytest", coverage_target: int = 80,
                   output_dir: str = "") -> dict:
    """AI自动生成单元测试
    Args:
        source_path: 源码文件路径
        source_code: 源码内容（当source_path为空时）
        framework: 测试框架 (pytest/unittest/jest/vitest)
        coverage_target: 目标覆盖率
        output_dir: 测试文件输出目录
    Returns:
        {"success": bool, "test_code": str, "test_file": str, "summary": str}
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "需要设置 OPENAI_API_KEY 环境变量"}

    # 获取源码
    code = source_code
    if source_path:
        fp = Path(source_path)
        if not fp.exists():
            return {"success": False, "error": f"文件不存在: {source_path}"}
        code = fp.read_text(encoding='utf-8')

    if not code:
        return {"success": False, "error": "请提供 source_path 或 source_code"}

    try:
        from api.agent_llm import call_llm

        test_prompt = f"""你是一个测试专家。为以下代码生成全面的单元测试。

目标框架: {framework}
目标覆盖率: {coverage_target}%
要求:
1. 覆盖所有函数和方法
2. 覆盖正常路径和边界情况
3. 包含 Mock 和 Fixture
4. 每个测试有清晰的描述

源码:
```python
{code[:6000]}
```

输出完整的测试代码在 ```{framework} 代码块中。"""

        messages = [{"role": "system", "content": f"你是一个 {framework} 测试专家，生成高质量的单元测试。"},
                    {"role": "user", "content": test_prompt}]
        content, _ = call_llm(messages, None, api_key)

        if not content:
            return {"success": False, "error": "测试生成失败"}

        import re
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', content, re.DOTALL)
        test_code = code_blocks[0][1].strip() if code_blocks else content.strip()

        # 写测试文件
        out_dir = Path(output_dir) if output_dir else Path("tests/generated")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        source_name = Path(source_path).stem if source_path else "module"
        test_fn = f"test_{source_name}_{int(__import__('time').time())}.py"
        test_file = out_dir / test_fn
        test_file.write_text(test_code, encoding='utf-8')

        # 计算测试数量
        test_count = len(re.findall(r'def test_', test_code))
        assert_count = len(re.findall(r'\bassert\b', test_code))

        return {
            "success": True,
            "test_code": test_code,
            "test_file": str(test_file),
            "summary": f"生成了 {test_count} 个测试，{assert_count} 个断言，目标覆盖率 {coverage_target}%"
        }

    except Exception as e:
        return {"success": False, "error": f"测试生成失败: {e}"}
