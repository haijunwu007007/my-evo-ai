import sys, asyncio

sys.path.insert(0, ".")


async def t():
    from backup_versioning import BackupVersioningManager

    m = BackupVersioningManager()
    print("1. OK:", m.module_name)
    await m.initialize()
    r = await m.execute("create_version", {"backup_id": "bk_main", "version": "2.1.0", "description": "升级修复"})
    vid = r["result"]["version_id"]
    print("2. version:", vid, "label:", r["result"]["label"])
    r = await m.execute("list_versions", {"backup_id": "bk_main"})
    print("3. versions:", r["result"]["total"])
    r = await m.execute("compare", {"version_id_a": r["result"]["versions"][0]["version_id"], "version_id_b": vid})
    print("4. compare:", r["result"]["diff_type"])
    r = await m.execute("rollback", {"version_id": vid, "reason": "测试回滚"})
    print("5. rollback:", r["result"]["status"])
    r = await m.execute("stats")
    print("6. stats: versions=", r["result"]["total_versions"], "rollbacks=", r["result"]["total_rollbacks"])
    h = m.health_check()
    print("7. health:", h["status"])
    await m.shutdown()
    print("PASSED")


asyncio.run(t())
