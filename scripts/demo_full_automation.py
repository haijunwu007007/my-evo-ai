#!/usr/bin/env python3
"""
AUTO-EVO-AI v7.0 — 全自动编排 Demo
=======================================
上市公司生产级 —— 跑通完整事件驱动闭环

演示内容:
  1. 自动发现所有模块
  2. 查看模块能力地图
  3. AI/关键词驱动的流水线编排
  4. 事件驱动触发
  5. Cron调度触发展示
  6. 统一数据库管理

用法:
    python scripts/demo_full_automation.py
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path

# 确保项目在路径上
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("demo")


async def main():
    logger.info("=" * 60)
    logger.info("AUTO-EVO-AI v7.0 全自动编排 Demo")
    logger.info("=" * 60)

    # ─── 1. 模块自动发现 ───
    logger.info("\n[1/6] 模块自动发现...")
    from modules._base.module_discovery import ModuleDiscoveryEngine

    engine = ModuleDiscoveryEngine(module_dir=str(BASE_DIR / "modules"))
    result = await engine.scan_all()
    logger.info(f"  ✔ 扫描完成: {result.summary()}")

    # ─── 2. 查看注册表 ───
    logger.info("\n[2/6] 模块注册表统计...")
    from modules._base.module_meta import ModuleRegistry

    registry = ModuleRegistry()
    stats = registry.get_stats()
    logger.info(f"  ✔ 总模块数: {stats['total_modules']}")
    logger.info(f"  ✔ 分组: {json.dumps(stats['groups'], ensure_ascii=False)}")
    logger.info(f"  ✔ 定时触发: {stats['scheduled']} 个")
    logger.info(f"  ✔ 事件驱动: {stats['event_driven']} 个")

    # ─── 3. 查看依赖关系图 ───
    logger.info("\n[3/6] 依赖关系图...")
    capability = registry.export_capability_map()
    logger.info(f"  ✔ 事件触发模块: {len(capability['triggers']['event'])}")
    logger.info(f"  ✔ Cron触发模块: {len(capability['triggers']['schedule'])}")
    for mid, deps in list(capability['dependencies'].items())[:8]:
        if deps:
            logger.info(f"     {mid} → 依赖: {deps}")

    # ─── 4. 智能编排 ───
    logger.info("\n[4/6] 智能编排流水线...")
    from modules._base.orchestration_engine import OrchestrationEngine
    from modules.event_bus import get_event_bus
    from modules._base.event_driven_orchestrator import PipelineEventBridge

    orch = OrchestrationEngine(registry=registry)
    event_bus = get_event_bus()
    bridge = PipelineEventBridge(event_bus)

    # 绑定事件桥接到编排引擎
    orch._event_bridge = bridge

    # 尝试关键词匹配流水线
    test_goals = [
        "扫描GitHub上的AI项目并通知飞书",
        "分析数据并生成报告",
        "备份数据库并发送通知",
        "系统健康检查",
    ]

    for goal in test_goals:
        logger.info(f"  目标: '{goal}'")
        result = await orch.process_goal(goal)
        if result.success:
            logger.info(f"    ✔ 成功! {result.summary}")
            for step in result.step_results:
                logger.info(f"       {step.get('module_id', '?')}: {'✔' if step.get('success') else '✗'} {step.get('duration_ms', 0):.0f}ms")
        else:
            logger.info(f"    ~ {result.summary}")

    # ─── 5. 事件驱动闭环 ───
    logger.info("\n[5/6] 事件驱动闭环演示...")

    # 注册事件监听
    events_received = []

    async def on_pipeline_complete(event_data):
        data = event_data.get("data", {})
        events_received.append(data)
        logger.info(f"   [事件] pipeline.complete: {data.get('module_ids', [])}")

    event_bus.subscribe("pipeline.complete", on_pipeline_complete)

    # 执行一个流水线，看事件是否能收到
    from modules._base.orchestration_engine import ExecutionMode
    result = await orch.execute_pipeline(
        ["github-scanner", "feishu-notifier"],
        params={"keywords": ["AI agent"], "min_stars": 50},
        mode=ExecutionMode.RELAXED,  # RELAXED模式：失败了继续
    )
    logger.info(f"  ✔ 流水线执行: {'成功' if result.success else '失败'} ({result.duration_ms:.0f}ms)")

    # 等待事件被处理
    await asyncio.sleep(0.5)
    logger.info(f"  ✔ 收到事件: {len(events_received)} 个")

    # ─── 6. 统一数据库管理 ───
    logger.info("\n[6/6] 统一数据库管理...")
    from modules._base.unified_db import UnifiedDBManager, get_db_manager

    db_manager = get_db_manager()
    discovered = db_manager.auto_discover()
    logger.info(f"  ✔ 自发现数据库: {len(discovered)} 个")

    report = db_manager.health_report()
    total_size = sum(
        db.get("size_kb", 0) for db in report["databases"].values()
    )
    total_tables = sum(
        db.get("table_count", 0) for db in report["databases"].values()
    )
    logger.info(f"  ✔ 总大小: {total_size:.0f} KB")
    logger.info(f"  ✔ 总表数: {total_tables}")

    # 展示前5个最大的数据库
    sorted_dbs = sorted(
        report["databases"].items(),
        key=lambda x: x[1].get("size_kb", 0),
        reverse=True,
    )[:5]
    for name, info in sorted_dbs:
        tables = info.get("table_count", 0)
        size = info.get("size_kb", 0)
        logger.info(f"     {name}: {tables}表, {size:.0f}KB")

    # ─── 汇总 ───
    logger.info("\n" + "=" * 60)
    logger.info("Demo 完成!")
    total = stats['total_modules']
    groups = len(stats['groups'])
    logger.info(f"  • {total} 个模块全面觉醒 (覆盖 {groups} 个分组)")
    logger.info(f"  • {stats['scheduled']} 个定时任务自动调度")
    logger.info(f"  • {stats['event_driven']} 个事件驱动模块")
    logger.info(f"  • {len(discovered)} 个数据库统一管理")
    logger.info(f"  • 事件驱动闭环已就绪")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
