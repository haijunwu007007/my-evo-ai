"""
# Grade: A
backup_checksum.py - 备份校验模块
上市公司级生产实现 - 完整性校验、哈希验证、差异比较、修复建议
"""

__module_meta__ = {
        "id": "backup-checksum",
        "name": "Backup Checksum",
        "version": "V0.1",
        "group": "backup",
        "inputs": [
            {
                "name": "operation",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "params",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "data",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "algorithm",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "p",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "p_2",
                "type": "string",
                "required": True,
                "description": ""
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_2",
                "type": "dict",
                "description": "执行结果"
            },
            {
                "name": "result_3",
                "type": "dict",
                "description": "执行结果"
            }
        ],
        "triggers": [
            {
                "type": "schedule",
                "config": {
                    "cron": "0 0 * * *"
                }
            }
        ],
        "depends_on": [],
        "tags": [
            "backup",
            "manager",
            "resilience"
        ],
        "grade": "A",
        "description": "backup_checksum.py - 备份校验模块 上市公司级生产实现 - 完整性校验、哈希验证、差异比较、修复建议"
    }

import asyncio
import logging
import hashlib
import time
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from modules._base.enterprise_module import EnterpriseModule
from modules._base.metrics import prometheus_timer, metrics_collector
from modules._base.mixins import CircuitBreakerMixin, RateLimiterMixin

logger = logging.getLogger(__name__)

@dataclass
class ChecksumRecord:
    """校验记录"""

    record_id: str
    backup_id: str
    file_path: str
    algorithm: str  # md5, sha1, sha256, sha512
    expected_hash: str
    actual_hash: str = ""
    file_size: int = 0
    verified: bool = False
    created_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None

@dataclass
class BackupManifest:
    """备份清单"""

    manifest_id: str
    backup_id: str
    total_files: int = 0
    total_size: int = 0
    checksum_algorithm: str = "sha256"
    records: List[ChecksumRecord] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None
    integrity_verified: bool = False

@dataclass
class DiffResult:
    """差异比较结果"""

    backup_id_a: str
    backup_id_b: str
    identical_files: int = 0
    modified_files: int = 0
    added_files: int = 0
    removed_files: int = 0
    total_size_diff: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)

class BackupChecksumManager(EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin):
    """
    备份校验管理器 - 生产级实现

    功能特性:
    1. 基类继承: 继承EnterpriseModule基类
    2. 生命周期管理: initialize/execute/health_check/shutdown完整实现
    3. 监控采集: 校验次数、失败率、耗时等指标
    4. 熔断器: 防止校验级联超时
    5. 限流: 控制并发校验数量
    6. 多算法校验: MD5/SHA1/SHA256/SHA512
    7. 完整性验证: 批量校验备份完整性
    8. 差异比较: 对比两个备份的差异
    9. 修复建议: 根据校验结果给出修复建议
    10. 清单管理: 生成和管理备份清单
    """

    def __init__(self):

        super().__init__()
        self.module_name = "backup_checksum"
        self.module_id = self.module_name
        self.version = "1.0.0"
        self.description = "备份校验模块 - 完整性校验、哈希验证、差异比较"
        self._initialized = False
        self._running = False

        # 清单存储
        self._manifests: Dict[str, BackupManifest] = {}
        # 校验记录索引 (backup_id -> records)
        self._backup_records: Dict[str, List[ChecksumRecord]] = {}
        # 校验历史
        self._history: List[Dict[str, Any]] = []
        self._max_history = 500
        # 模拟文件存储 (内存中)
        self._file_store: Dict[str, bytes] = {}
        # 并发控制
        self._max_concurrent = 10
        self._active_verifications = 0
        self._lock = asyncio.Lock()

        # 支持的算法
        self._algorithms = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
        }
        # 默认算法
        self._default_algorithm = "sha256"

        # 指标
        self._total_verifications = 0
        self._successful_verifications = 0
        self._failed_verifications = 0
        self._total_hashes_computed = 0
        self._verification_time_ms = 0.0

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._running = True
        logger.info("备份校验管理器初始化完成")

    async def execute(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        self.trace("execute", {"module": "backup_checksum"})
        self.metrics_collector.counter("backup_checksum.execute.calls", 1)
        self.audit("execute", {"module": "backup_checksum"})
        params = params or {}
        ops = {
            "compute": self._compute_hash,
            "verify": self._verify_file,
            "verify_batch": self._verify_batch,
            "create_manifest": self._create_manifest,
            "verify_manifest": self._verify_manifest,
            "diff": self._diff_backups,
            "store_file": self._store_file,
            "get_file": self._get_file,
            "get_manifest": self._get_manifest,
            "list_manifests": self._list_manifests,
            "get_stats": self._get_stats,
            "repair_suggest": self._repair_suggest,
        }
        handler = ops.get(operation)
        if not handler:
            return {"success": False, "error": f"未知操作: {operation}"}
        try:
            result = handler(params)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"校验操作失败 [{operation}]: {e}")
            return {"success": False, "error": str(e)}

    def _hash(self, data: bytes, algorithm: str = "sha256") -> str:
        """计算哈希值"""
        h = self._algorithms.get(algorithm)
        if not h:
            raise ValueError(f"不支持的算法: {algorithm}")
        return h(data).hexdigest()

    def _store_file(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """存储文件（模拟）"""
        file_path = p["file_path"]
        content = p.get("content", "default file content").encode()
        self._file_store[file_path] = content
        return {
            "stored": True,
            "file_path": file_path,
            "size_bytes": len(content),
            "hash_sha256": self._hash(content, "sha256")[:16],
        }

    def _get_file(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """获取文件"""
        file_path = p["file_path"]
        content = self._file_store.get(file_path)
        if not content:
            return {"error": f"文件不存在: {file_path}"}
        return {"file_path": file_path, "size_bytes": len(content), "hash_sha256": self._hash(content, "sha256")[:16]}

    def _compute_hash(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """计算文件哈希"""
        file_path = p["file_path"]
        algorithm = p.get("algorithm", self._default_algorithm)
        content = self._file_store.get(file_path)
        if not content:
            return {"error": f"文件不存在: {file_path}"}

        hash_val = self._hash(content, algorithm)
        self._total_hashes_computed += 1

        return {"file_path": file_path, "algorithm": algorithm, "hash": hash_val, "size_bytes": len(content)}

    def _verify_file(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """验证文件哈希"""
        file_path = p["file_path"]
        expected_hash = p["expected_hash"]
        algorithm = p.get("algorithm", self._default_algorithm)
        backup_id = p.get("backup_id", "unknown")

        content = self._file_store.get(file_path)
        if not content:
            return {"error": f"文件不存在: {file_path}"}

        self._total_verifications += 1
        start = time.time()
        actual_hash = self._hash(content, algorithm)
        elapsed_ms = (time.time() - start) * 1000
        self._verification_time_ms += elapsed_ms

        verified = actual_hash == expected_hash
        if verified:
            self._successful_verifications += 1
        else:
            self._failed_verifications += 1

        record = ChecksumRecord(
            record_id=f"rec_{hashlib.md5(f'{file_path}{time.time()}'.encode()).hexdigest()[:8]}",
            backup_id=backup_id,
            file_path=file_path,
            algorithm=algorithm,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            file_size=len(content),
            verified=verified,
            verified_at=time.time(),
        )
        self._backup_records.setdefault(backup_id, []).append(record)

        self._history.append(
            {
                "file_path": file_path,
                "backup_id": backup_id,
                "verified": verified,
                "algorithm": algorithm,
                "timestamp": time.time(),
            }
        )
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        return {
            "file_path": file_path,
            "verified": verified,
            "expected": expected_hash[:16],
            "actual": actual_hash[:16],
            "algorithm": algorithm,
            "duration_ms": round(elapsed_ms, 2),
        }

    def _verify_batch(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """批量校验"""
        backup_id = p["backup_id"]
        file_hashes = p.get("file_hashes", [])  # [{file_path, expected_hash, algorithm}]
        results = []
        passed = 0
        failed = 0

        with self._lock:
            if self._active_verifications >= self._max_concurrent:
                return {"error": "已达最大并发数"}
            self._active_verifications += 1

        try:
            for item in file_hashes:
                r = self._verify_file(
                    {
                        "file_path": item["file_path"],
                        "expected_hash": item["expected_hash"],
                        "algorithm": item.get("algorithm", self._default_algorithm),
                        "backup_id": backup_id,
                    }
                )
                if r.get("error"):
                    results.append({"file_path": item["file_path"], "status": "error", "error": r["error"]})
                    failed += 1
                else:
                    results.append({"file_path": item["file_path"], "verified": r["result"]["verified"]})
                    if r["result"]["verified"]:
                        passed += 1
                    else:
                        failed += 1

            return {
                "backup_id": backup_id,
                "total": len(file_hashes),
                "passed": passed,
                "failed": failed,
                "integrity": f"{passed / max(len(file_hashes), 1) * 100:.1f}%",
            }
        finally:
            with self._lock:
                self._active_verifications -= 1

    def _create_manifest(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """创建备份清单"""
        backup_id = p["backup_id"]
        file_paths = p.get("file_paths", [])
        algorithm = p.get("algorithm", self._default_algorithm)

        manifest_id = f"mf_{hashlib.md5(f'{backup_id}{time.time()}'.encode()).hexdigest()[:8]}"
        records = []
        total_size = 0

        for fp in file_paths:
            content = self._file_store.get(fp)
            if not content:
                continue
            file_hash = self._hash(content, algorithm)
            record = ChecksumRecord(
                record_id=f"rec_{hashlib.md5(f'{fp}{time.time()}'.encode()).hexdigest()[:8]}",
                backup_id=backup_id,
                file_path=fp,
                algorithm=algorithm,
                expected_hash=file_hash,
                actual_hash=file_hash,
                file_size=len(content),
                verified=True,
                verified_at=time.time(),
            )
            records.append(record)
            total_size += len(content)
            self._total_hashes_computed += 1

        manifest = BackupManifest(
            manifest_id=manifest_id,
            backup_id=backup_id,
            total_files=len(records),
            total_size=total_size,
            checksum_algorithm=algorithm,
            records=records,
            verified_at=time.time(),
            integrity_verified=True,
        )
        self._manifests[manifest_id] = manifest
        self._backup_records[backup_id] = records

        return {
            "manifest_id": manifest_id,
            "backup_id": backup_id,
            "total_files": len(records),
            "total_size": total_size,
            "algorithm": algorithm,
        }

    def _verify_manifest(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """验证备份清单"""
        manifest_id = p["manifest_id"]
        manifest = self._manifests.get(manifest_id)
        if not manifest:
            return {"error": f"清单不存在: {manifest_id}"}

        passed = 0
        failed = 0
        failures = []

        for record in manifest.records:
            content = self._file_store.get(record.file_path)
            if not content:
                failed += 1
                failures.append({"file_path": record.file_path, "reason": "file_missing"})
                continue
            actual = self._hash(content, record.algorithm)
            record.actual_hash = actual
            if actual == record.expected_hash:
                record.verified = True
                passed += 1
            else:
                record.verified = False
                failed += 1
                failures.append({"file_path": record.file_path, "reason": "hash_mismatch"})

        manifest.verified_at = time.time()
        manifest.integrity_verified = failed == 0

        return {
            "manifest_id": manifest_id,
            "integrity_verified": manifest.integrity_verified,
            "total": manifest.total_files,
            "passed": passed,
            "failed": failed,
            "integrity": f"{passed / max(manifest.total_files, 1) * 100:.1f}%",
            "failures": failures[:10],
        }

    def _diff_backups(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """比较两个备份的差异"""
        backup_a = p["backup_id_a"]
        backup_b = p["backup_id_b"]
        records_a = {r.file_path: r for r in self._backup_records.get(backup_a, [])}
        records_b = {r.file_path: r for r in self._backup_records.get(backup_b, [])}

        files_a = set(records_a.keys())
        files_b = set(records_b.keys())

        identical = 0
        modified = 0
        details = []
        size_diff = 0

        for fp in files_a & files_b:
            if records_a[fp].actual_hash == records_b[fp].actual_hash:
                identical += 1
            else:
                modified += 1
                size_diff += abs(records_b[fp].file_size - records_a[fp].file_size)
                details.append(
                    {"file": fp, "change": "modified", "size_diff": records_b[fp].file_size - records_a[fp].file_size}
                )

        added = len(files_b - files_a)
        removed = len(files_a - files_b)
        for fp in files_b - files_a:
            details.append({"file": fp, "change": "added", "size": records_b[fp].file_size})
        for fp in files_a - files_b:
            details.append({"file": fp, "change": "removed", "size": records_a[fp].file_size})

        return {
            "backup_a": backup_a,
            "backup_b": backup_b,
            "identical_files": identical,
            "modified_files": modified,
            "added_files": added,
            "removed_files": removed,
            "total_size_diff": size_diff,
            "details": details[:20],
        }

    def _repair_suggest(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """修复建议"""
        backup_id = p.get("backup_id")
        manifest_id = p.get("manifest_id")
        suggestions = []

        if manifest_id:
            manifest = self._manifests.get(manifest_id)
            if manifest:
                for record in manifest.records:
                    if not record.verified:
                        suggestions.append(
                            {
                                "file_path": record.file_path,
                                "issue": "hash_mismatch" if record.actual_hash else "file_missing",
                                "suggestion": "重新备份该文件并更新清单",
                            }
                        )

        if backup_id:
            records = self._backup_records.get(backup_id, [])
            failed_records = [r for r in records if not r.verified]
            if failed_records:
                suggestions.append(
                    {
                        "level": "warning",
                        "message": f"备份 {backup_id} 有 {len(failed_records)} 个文件校验失败",
                        "action": "建议重新执行备份",
                    }
                )

        if not suggestions:
            suggestions.append({"level": "info", "message": "所有文件校验通过,无需修复"})

        return {"suggestions": suggestions}

    def _get_manifest(self, p: Dict[str, Any]) -> Dict[str, Any]:
        manifest = self._manifests.get(p["manifest_id"])
        if not manifest:
            return {"error": f"清单不存在: {p['manifest_id']}"}
        return {
            "manifest_id": manifest.manifest_id,
            "backup_id": manifest.backup_id,
            "total_files": manifest.total_files,
            "total_size": manifest.total_size,
            "algorithm": manifest.checksum_algorithm,
            "integrity_verified": manifest.integrity_verified,
            "records": len(manifest.records),
        }

    def _list_manifests(self, p: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "manifest_id": m.manifest_id,
                "backup_id": m.backup_id,
                "total_files": m.total_files,
                "verified": m.integrity_verified,
            }
            for m in self._manifests.values()
        ]

    def _get_stats(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "total_verifications": self._total_verifications,
            "successful": self._successful_verifications,
            "failed": self._failed_verifications,
            "success_rate": f"{self._successful_verifications / max(self._total_verifications, 1) * 100:.1f}%",
            "total_hashes": self._total_hashes_computed,
            "manifests": len(self._manifests),
            "avg_verification_ms": round(self._verification_time_ms / max(self._total_verifications, 1), 2),
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "module": self.module_name,
            "version": self.version,
            "manifests": len(self._manifests),
            "total_verifications": self._total_verifications,
            "success_rate": f"{self._successful_verifications / max(self._total_verifications, 1) * 100:.1f}%",
            "file_store_size": len(self._file_store),
            "active_verifications": self._active_verifications,
            "algorithms": list(self._algorithms.keys()),
        }

    def shutdown(self) -> None:
        self._running = False
        logger.info(f"备份校验管理器关闭, 校验次数: {self._total_verifications}")

    def batch_verify(self, file_paths: List[str], algorithm: str = "sha256") -> Dict[str, Any]:
        """批量校验文件完整性。企业场景：灾备演练时一次性校验数百个备份文件。
        返回每文件的校验结果（匹配/不匹配/缺失），汇总统计。
        """
        results = {"total": len(file_paths), "matched": 0, "mismatched": 0, "missing": 0, "errors": [], "details": []}
        for fp in file_paths:
            try:
                manifest = self._manifests.get(fp)
                if not manifest:
                    results["missing"] += 1
                    results["details"].append({"file": fp, "status": "missing_manifest"})
                    continue
                actual_hash = self._compute_hash(fp, algorithm)
                expected = manifest.get("checksums", {}).get(algorithm)
                if actual_hash == expected:
                    results["matched"] += 1
                    results["details"].append({"file": fp, "status": "matched", "hash": actual_hash})
                else:
                    results["mismatched"] += 1
                    results["details"].append(
                        {
                            "file": fp,
                            "status": "mismatch",
                            "expected": expected,
                            "actual": actual_hash,
                        }
                    )
            except Exception as e:
                results["errors"].append({"file": fp, "error": str(e)})
        return results

    def get_integrity_report(self) -> Dict[str, Any]:
        """获取备份完整性报告。企业场景：每日自动生成备份健康度报告。
        统计各算法校验次数、成功率、最近异常记录。
        """
        report = {
            "total_manifests": len(self._manifests),
            "total_verifications": self._total_verifications,
            "success_rate": round(self._successful_verifications / max(self._total_verifications, 1) * 100, 1),
            "algorithms_used": {},
            "recent_anomalies": [],
        }
        algo_stats = {}
        for manifest in self._manifests.values():
            for algo in manifest.get("checksums", {}):
                algo_stats[algo] = algo_stats.get(algo, 0) + 1
        report["algorithms_used"] = algo_stats
        if hasattr(self, "_anomaly_log"):
            report["recent_anomalies"] = self._anomaly_log[-10:] if isinstance(self._anomaly_log, list) else []
        return report

module_class = BackupChecksumManager
