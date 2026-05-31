#!/usr/bin/env python3
"""为所有API路由添加docstring，让Swagger文档有描述"""
import re, ast, os
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent / "api"

def generate_docstring(func_name: str, route: str, method: str) -> str:
    """根据函数名和路由生成中文描述"""
    desc_map = {
        "system_diagnosis": "系统诊断信息：运行时长、版本",
        "modules_diagnosis": "模块诊断：注册模块列表与统计",
        "config_list": "获取所有配置项",
        "config_entries": "获取配置条目列表（扁平化）",
        "config_get": "获取指定配置项的值",
        "config_set": "更新指定配置项",
        "config_batch": "批量更新配置",
        "config_delete": "删除指定配置项",
        "config_stats": "配置统计信息：分组与总量",
        "config_list_all": "按分组列出所有配置",
        "config_save": "持久化保存当前配置到文件",
        "config_reload": "重新加载配置文件",
        "persistence_status": "持久化状态检查",
        "monitor_realtime": "实时系统监控：CPU/内存/磁盘/网络/请求量",
        "ws_status": "WebSocket连接状态",
        "system_metrics": "系统指标：运行时间/请求数/错误数/缓存命中",
        "rate_limit_status": "限流状态查询",
        "serve_dashboard": "返回 Dashboard 管理界面",
        "health_check": "健康检查端点",
        "ws_stats": "WebSocket统计信息",
        "ws_channels": "可用WebSocket频道列表",
        "ws_history": "WebSocket消息历史",
        "ws_broadcast": "广播WebSocket消息（管理用）",
        "auth_login": "用户登录认证",
        "auth_status": "认证状态检查",
        "auth_logout": "用户登出",
        "scheduler_status": "调度器状态",
        "scheduler_tasks": "获取调度任务列表",
        "create_scheduler_task": "创建调度任务",
        "toggle_scheduler_task": "启用/禁用调度任务",
        "delete_scheduler_task": "删除调度任务",
        "trigger_scheduler_task": "立即触发调度任务",
        "event_stats": "事件统计",
        "event_rules": "事件规则列表",
        "create_event_rule": "创建事件规则",
        "delete_event_rule": "删除事件规则",
        "modules_list": "模块列表（分页/搜索/过滤）",
        "modules_categories": "模块分类统计",
        "modules_rescan": "重新扫描模块目录",
        "module_execute": "执行模块动作",
        "module_detail": "模块详情",
        "monitor_realtime": "实时系统监控指标",
        "coordinator_status": "协调器状态",
        "coordinator_capabilities": "协调器能力列表",
        "coordinator_execute": "执行协调任务",
        "queue_stats": "任务队列统计",
        "queue_tasks": "队列任务列表",
        "enqueue_task": "入队任务",
        "cancel_task": "取消队列任务",
        "retry_task": "重试队列任务",
        "pipeline_list": "管线列表",
        "create_pipeline": "创建管线",
        "execute_pipeline": "执行管线",
        "delete_pipeline": "删除管线",
        "template_list": "模板列表",
        "apply_template": "应用模板",
        "security_status": "安全状态",
        "config_list": "系统配置列表",
        "auth_status": "认证状态",
    }
    if func_name in desc_map:
        return desc_map[func_name]
    # fallback
    name = func_name.replace("_", " ").title()
    return f"{name} - {method.upper()} {route}"

def patch_file(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    original = content
    # 匹配: @router.get|post|put|delete("/path")
    # 下一行: async def func(...):
    pattern = re.compile(
        r'(@router\.(get|post|put|delete|patch)\("([^"]*)"[^)]*\))\s*\n\s*(async )?def (\w+)',
    )
    def replacer(m):
        decorator = m.group(1)
        method = m.group(2)
        route_path = m.group(3)
        func_name = m.group(5)
        # 检查函数体是否已有 docstring
        full_match = m.group(0)
        # 获取函数后的内容
        pos = m.end()
        rest = content[pos:pos+200]
        if '"""' in rest or "'''" in rest:
            return full_match  # 已有docstring，跳过
        doc = generate_docstring(func_name, route_path, method)
        return f'{decorator}\n    """{doc}"""\n    async def {func_name}'
    new_content = pattern.sub(replacer, content)
    if new_content != original:
        filepath.write_text(new_content, encoding="utf-8")
        return True
    return False

if __name__ == "__main__":
    count = 0
    for f in sorted(api_dir.glob("routes_*.py")):
        if patch_file(f):
            print(f"  patched: {f.name}")
            count += 1
    print(f"共计修改 {count} 个文件")
