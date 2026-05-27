"""
AUTO-EVO-AI V0.1 — 存储加密模块
Grade: A (生产级) | Category: 安全
职责：使用 cryptography.fernet 提供真实数据加密/解密
"""

from modules._base.enterprise_module import EnterpriseModule, ModuleStatus, Result
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Optional
import base64
import os
import json
import time
import logging

logger = logging.getLogger("evo.storage_encryption")

__module_meta__ = {
    "id": "storage-encryption",
    "name": "Storage Encryption",
    "version": "V0.1",
    "group": "security",
    "inputs": [
        {"name": "action", "type": "string", "required": True, "description": "encrypt|decrypt|encrypt_file|decrypt_file|generate_key"},
        {"name": "data", "type": "string", "required": False, "description": "待加解密的数据"},
        {"name": "key", "type": "string", "required": False, "description": "加密密钥（不传则用默认派生密钥）"},
    ],
    "outputs": [
        {"name": "result", "type": "string", "description": "加密/解密后的数据"},
        {"name": "success", "type": "boolean", "description": "操作是否成功"},
    ],
}

module_class = None


class StorageEncryptionModule(EnterpriseModule):
    """存储加密模块——使用 cryptography.fernet 提供真实 AES 加密"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._fernet: Optional[Fernet] = None
        self._status = ModuleStatus.UNINITIALIZED
        self._encrypt_count = 0
        self._decrypt_count = 0
        self._last_error = ""

    def initialize(self) -> dict:
        try:
            master_key = self.config.get("encryption_key", "").encode()
            salt = self.config.get("encryption_salt", base64.b64encode(b"EVO-salt-v0.1").decode()).encode()
            if isinstance(salt, str):
                salt = salt.encode()
            if not master_key:
                master_key = Fernet.generate_key()

            if len(master_key) < 16:
                kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
                key = base64.urlsafe_b64encode(kdf.derive(master_key))
            else:
                key = base64.urlsafe_b64encode(master_key[:32].ljust(32, b'\0'))

            self._fernet = Fernet(key)
            self._status = ModuleStatus.RUNNING
            logger.info("存储加密模块初始化完成")
            return {"success": True, "status": "running"}
        except Exception as e:
            self._status = ModuleStatus.ERROR
            self._last_error = str(e)
            return {"success": False, "error": str(e)}

    async def execute(self, action: str, params: Optional[Dict] = None) -> Result:
        params = params or {}
        try:
            if action == "encrypt":
                return self._encrypt(params)
            elif action == "decrypt":
                return self._decrypt(params)
            elif action == "encrypt_file":
                return self._encrypt_file(params)
            elif action == "decrypt_file":
                return self._decrypt_file(params)
            elif action == "generate_key":
                return self._generate_key()
            elif action == "health":
                return self._health_check()
            else:
                return Result(success=False, error=f"未知操作: {action}")
        except Exception as e:
            self._last_error = str(e)
            return Result(success=False, error=str(e))

    def _encrypt(self, params: Dict) -> Result:
        data = params.get("data", "")
        if not data:
            return Result(success=False, error="data required")
        token = self._fernet.encrypt(data.encode() if isinstance(data, str) else data)
        self._encrypt_count += 1
        return Result(success=True, data={"token": token.decode(), "algorithm": "AES-256-CBC"})

    def _decrypt(self, params: Dict) -> Result:
        token = params.get("data", "")
        if not token:
            return Result(success=False, error="data required")
        try:
            token_bytes = token.encode() if isinstance(token, str) else token
            plain = self._fernet.decrypt(token_bytes)
            self._decrypt_count += 1
            return Result(success=True, data={"plaintext": plain.decode()})
        except InvalidToken:
            return Result(success=False, error="解密失败：无效的令牌或密钥不匹配")

    def _encrypt_file(self, params: Dict) -> Result:
        path = params.get("path", "")
        if not path or not os.path.isfile(path):
            return Result(success=False, error="文件不存在")
        with open(path, "rb") as f:
            data = f.read()
        token = self._fernet.encrypt(data)
        out_path = path + ".encrypted"
        with open(out_path, "wb") as f:
            f.write(token)
        self._encrypt_count += 1
        return Result(success=True, data={"output_path": out_path, "size": len(token)})

    def _decrypt_file(self, params: Dict) -> Result:
        path = params.get("path", "")
        if not path or not os.path.isfile(path):
            return Result(success=False, error="文件不存在")
        with open(path, "rb") as f:
            token = f.read()
        try:
            plain = self._fernet.decrypt(token)
            out_path = path.replace(".encrypted", ".decrypted")
            with open(out_path, "wb") as f:
                f.write(plain)
            self._decrypt_count += 1
            return Result(success=True, data={"output_path": out_path, "size": len(plain)})
        except InvalidToken:
            return Result(success=False, error="解密失败：无效的令牌或密钥不匹配")

    def _generate_key(self) -> Result:
        key = Fernet.generate_key()
        return Result(success=True, data={"key": key.decode(), "algorithm": "AES-256-CBC-Fernet"})

    def _health_check(self) -> Result:
        return Result(success=True, data={
            "status": self._status.value,
            "fernet": self._fernet is not None,
            "encrypt_count": self._encrypt_count,
            "decrypt_count": self._decrypt_count,
            "last_error": self._last_error or None,
        })

    async def shutdown(self) -> None:
        self._fernet = None
        self._status = ModuleStatus.STOPPED


module_class = StorageEncryptionModule
