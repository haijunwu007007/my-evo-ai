@echo off
REM AUTO-EVO-AI 开发工具链安装脚本 (Windows)
REM 用于统一代码风格和类型检查

echo === 安装开发工具链 ===

pip install ruff mypy pre-commit

echo.
echo === 配置 Pre-commit Hooks ===

copy NUL > .pre-commit-config.yaml
(
echo repos:
echo   - repo: https://github.com/astral-sh/ruff-pre-commit
echo     rev: v0.5.0
echo     hooks:
echo       - id: ruff
echo         args: [--fix]
echo       - id: ruff-format
echo.
echo   - repo: https://github.com/pre-commit/mirrors-mypy
echo     rev: v1.11.0
echo     hooks:
echo       - id: mypy
echo         args: [--ignore-missing-imports]
echo         exclude: ^(modules/_|_archive/^)
echo.
echo   - repo: https://github.com/pre-commit/pre-commit-hooks
echo     rev: v4.6.0
echo     hooks:
echo       - id: trailing-whitespace
echo       - id: end-of-file-fixer
echo       - id: check-yaml
echo       - id: check-json
echo       - id: check-toml
) > .pre-commit-config.yaml

pre-commit install

echo.
echo === 完成！===
echo 运行 ruff check ./modules/ 检查代码风格
echo 运行 ruff format ./modules/ 自动格式化
