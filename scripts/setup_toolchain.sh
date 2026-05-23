#!/bin/bash
# AUTO-EVO-AI 开发工具链安装脚本
# 用于统一代码风格和类型检查

set -e

echo "=== 安装开发工具链 ==="

pip install ruff mypy pre-commit

echo ""
echo "=== 配置 Pre-commit Hooks ==="

cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        exclude: ^(modules/_|_archive/)
        additional_dependencies: []

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
EOF

pre-commit install

echo ""
echo "=== 完成！==="
echo "运行 ruff check ./modules/ 检查代码风格"
echo "运行 ruff format ./modules/ 自动格式化"
echo "运行 mypy modules/ 进行类型检查"
