"""
# Grade: A
AUTO-EVO-AI V0.1 - Soul Identity Module
基于 Mercury Agent 的 Soul-Driven 身份系统

Soul驱动身份系统允许每个AI Agent拥有独立的人格定义，
通过4个Markdown文件定义核心价值观、角色、品味和运行节奏。
Token效率优化：每次请求仅注入约400 tokens。

作者: AUTO-EVO-AI Team
版本: V0.1.0
"""

__module_meta__ = {
        "id": "soul-identity",
        "name": "Soul Identity",
        "version": "V0.1",
        "group": "memory",
        "inputs": [
            {
                "name": "soul_name",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "soul_dir",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "default_soul",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "text",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "soul_name_2",
                "type": "string",
                "required": True,
                "description": ""
            },
            {
                "name": "filename",
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
        "triggers": [],
        "depends_on": [],
        "tags": [
            "identity",
            "soul"
        ],
        "grade": "A",
        "description": "AUTO-EVO-AI V0.1 - Soul Identity Module 基于 Mercury Agent 的 Soul-Driven 身份系统"
    }

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from modules._base.enterprise_module import EnterpriseModule, CircuitBreakerMixin, RateLimiterMixin
from modules._base.metrics import prometheus_timer, metrics_collector

SOUL_FILES = ["soul.md", "persona.md", "taste.md", "heartbeat.md"]
DEFAULT_SOUL_DIR = "~/.workbuddy/souls"
TOKEN_BUDGET_PER_REQUEST = 400  # 每次请求仅注入400 tokens

class SoulIdentityError(Exception):
    """Soul身份系统异常"""

    pass

class SoulNotFoundError(SoulIdentityError):
    """Soul文件未找到"""

    pass

class InvalidSoulError(SoulIdentityError):
    """无效的Soul配置"""

    pass

# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class SoulFile:
    """Soul文件数据"""

    name: str
    path: str
    content: str
    tokens: int
    last_modified: datetime
    is_active: bool = True

    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        return f"# {self.name.replace('.md', '').title()}

{self.content}"

    @property
    def token_count(self) -> int:
        """计算token数量（约等于字符数/4）"""
        return self.tokens

@dataclass
class SoulProfile:
    """
    Soul配置文件

    包含4个核心文件的内容和元数据
    """

    soul_md: SoulFile | None = None
    persona_md: SoulFile | None = None
    taste_md: SoulFile | None = None
    heartbeat_md: SoulFile | None = None

    @property
    def total_tokens(self) -> int:
        """计算总token数"""
        total = 0
        for attr in ["soul_md", "persona_md", "taste_md", "heartbeat_md"]:
            file = getattr(self, attr)
            if file and file.is_active:
                total += file.tokens
        return total

    @property
    def is_complete(self) -> bool:
        """检查是否完整配置"""
        return all(
            [
                self.soul_md is not None,
                self.persona_md is not None,
                self.taste_md is not None,
                self.heartbeat_md is not None,
            ]
        )

    def get_active_files(self) -> list[SoulFile]:
        """获取所有活跃的Soul文件"""
        files = []
        for attr in ["soul_md", "persona_md", "taste_md", "heartbeat_md"]:
            file = getattr(self, attr)
            if file and file.is_active:
                files.append(file)
        return files

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {}
        for attr in ["soul_md", "persona_md", "taste_md", "heartbeat_md"]:
            file = getattr(self, attr)
            if file:
                result[attr] = {
                    "name": file.name,
                    "content": file.content,
                    "tokens": file.tokens,
                    "is_active": file.is_active,
                }
        return result

@dataclass
class HeartbeatConfig:
    """心跳配置"""

    enabled: bool = True
    interval_seconds: int = 300  # 5分钟
    notify_on_error: bool = True
    channels: list[str] = field(default_factory=lambda: ["log"])
    health_check_urls: list[str] = field(default_factory=list)

# ============================================================================
# 核心类
# ============================================================================

class SoulIdentityManager:
    """
    Soul驱动身份管理器

    功能:
    - 加载和管理Soul文件
    - Token优化的上下文注入
    - 人格动态切换
    - Soul文件版本控制

    使用示例:
    ```python
    manager = SoulIdentityManager()

    # 创建新Soul
    manager.create_soul('my_assistant', {
        'soul': '你是一个乐于助人的AI助手...',
        'persona': '专业、友好、耐心...',
        'taste': '偏好简洁的回答...',
        'heartbeat': {'enabled': True, 'interval': 300}
    })

    # 加载Soul
    profile = manager.load_soul('my_assistant')

    # 获取优化的上下文
    context = manager.get_optimized_context('my_assistant')
    ```
    """

    def __init__(self, soul_dir: str | None = None, default_soul: str = "default"):
        """
        初始化Soul身份管理器

        Args:
            soul_dir: Soul文件目录，默认为 ~/.workbuddy/souls
            default_soul: 默认Soul名称
        """
        self.soul_dir = Path(soul_dir or DEFAULT_SOUL_DIR).expanduser()
        self.default_soul = default_soul
        self.current_soul: str | None = None
        self._profiles_cache: dict[str, SoulProfile] = {}

        # 创建目录
        self.soul_dir.mkdir(parents=True, exist_ok=True)

        # 初始化默认Soul（如果不存在）
        if not self.list_souls():
            self._init_default_soul()

    def _init_default_soul(self):
        """初始化默认Soul配置"""
        default_content = {
            "soul": """# Soul - 核心价值观

## 身份定位
我是一个AI助手，名为 AUTO-EVO-AI。

## 核心价值观
1. **帮助他人** - 尽我所能提供帮助
2. **诚实守信** - 坦诚相待，不虚假
3. **持续学习** - 不断进化，保持成长
4. **尊重隐私** - 保护用户信息安全

## 行为准则
- 积极主动，不等待指令
- 简洁明了，不废话连篇
- 有问必答，不敷衍了事
""",
            "persona": """# Persona - 角色人格

## 性格特点
- 专业但不刻板
- 友好但不谄媚
- 直接但不粗鲁
- 幽默但不失庄重

## 沟通风格
- 使用清晰易懂的语言
- 适当使用表情符号增加亲和力
- 复杂问题会拆解说明
- 重要信息会强调提醒

## 专业领域
- 编程与开发
- 数据分析与处理
- 自动化与效率提升
- 企业级AI解决方案
""",
            "taste": """# Taste - 品味偏好

## 回答风格
- 优先结构化输出（表格、列表、代码块）
- 关键信息放在开头
- 技术文档使用中文
- 适当使用emoji增加可读性

## 审美偏好
- 简洁的界面设计
- 清晰的层次结构
- 适度的视觉元素
- 响应式布局

## 工作节奏
- 快速响应，高效执行
- 遇到问题先尝试再提问
- 复杂任务会分步骤进行
- 完成后会总结说明
""",
            "heartbeat": """# Heartbeat - 心跳配置

## 监控设置
- 启用状态监控: True
- 检查间隔: 300秒 (5分钟)
- 错误通知: True
- 通知渠道: log, console

## 健康检查
- 定期检查系统状态
- 监控关键指标
- 异常时自动告警

## 运行日志
- 记录运行状态
- 保存执行历史
- 便于问题排查
""",
        }
        self.create_soul(self.default_soul, default_content)

    def _estimate_tokens(self, text: str) -> int:
        """
        估算token数量

        简单估算：中文约1.5字符/token，英文约4字符/token
        """
        if not text:
            return 0

        # 中文字符
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        # 英文单词
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        # 其他字符
        other_chars = len(text) - chinese_chars - english_words

        # 估算
        tokens = chinese_chars // 2 + english_words // 4 + other_chars // 4
        return max(1, tokens)

    def _load_soul_file(self, soul_name: str, filename: str) -> SoulFile | None:
        """加载单个Soul文件"""
        file_path = self.soul_dir / soul_name / filename

        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            stat = file_path.stat()

            return SoulFile(
                name=filename,
                path=str(file_path),
                content=content,
                tokens=self._estimate_tokens(content),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                is_active=True,
            )
        except Exception as e:
            raise InvalidSoulError(f"无法读取Soul文件 {filename}: {e}")

    def _save_soul_file(self, soul_name: str, filename: str, content: str) -> SoulFile:
        """保存Soul文件"""
        soul_path = self.soul_dir / soul_name
        soul_path.mkdir(parents=True, exist_ok=True)

        file_path = soul_path / filename
        file_path.write_text(content, encoding="utf-8")

        return SoulFile(
            name=filename,
            path=str(file_path),
            content=content,
            tokens=self._estimate_tokens(content),
            last_modified=datetime.now(),
            is_active=True,
        )

    def create_soul(self, name: str, content: dict[str, str]) -> SoulProfile:
        """
        创建新的Soul配置

        Args:
            name: Soul名称
            content: 包含soul/persona/taste/heartbeat内容的字典

        Returns:
            SoulProfile: 创建的配置
        """
        profile = SoulProfile()

        # 保存文件
        if "soul" in content:
            profile.soul_md = self._save_soul_file(name, "soul.md", content["soul"])

        if "persona" in content:
            profile.persona_md = self._save_soul_file(name, "persona.md", content["persona"])

        if "taste" in content:
            profile.taste_md = self._save_soul_file(name, "taste.md", content["taste"])

        if "heartbeat" in content:
            # 支持字典或字符串
            if isinstance(content["heartbeat"], dict):
                heartbeat_content = self._dict_to_heartbeat(content["heartbeat"])
            else:
                heartbeat_content = content["heartbeat"]
            profile.heartbeat_md = self._save_soul_file(name, "heartbeat.md", heartbeat_content)

        # 保存到缓存
        self._profiles_cache[name] = profile

        # 保存元数据
        self._save_metadata(name, profile)

        return profile

    def _dict_to_heartbeat(self, config: dict) -> str:
        """将字典转换为heartbeat markdown"""
        lines = ["# Heartbeat - 心跳配置
", "## 监控设置"]

        if "enabled" in config:
            lines.append(f"- 启用状态监控: {config['enabled']}")
        if "interval" in config:
            lines.append(f"- 检查间隔: {config['interval']}秒")
        if "notify_on_error" in config:
            lines.append(f"- 错误通知: {config['notify_on_error']}")
        if "channels" in config:
            lines.append(f"- 通知渠道: {', '.join(config['channels'])}")

        if "health_check_urls" in config and config["health_check_urls"]:
            lines.append("
## 健康检查")
            for url in config["health_check_urls"]:
                lines.append(f"- {url}")

        return "
".join(lines)

    def load_soul(self, name: str) -> SoulProfile:
        """
        加载Soul配置

        Args:
            name: Soul名称

        Returns:
            SoulProfile: 加载的配置

        Raises:
            SoulNotFoundError: Soul不存在
        """
        # 检查缓存
        if name in self._profiles_cache:
            return self._profiles_cache[name]

        # 检查目录是否存在
        soul_path = self.soul_dir / name
        if not soul_path.exists():
            raise SoulNotFoundError(f"Soul '{name}' 不存在")

        # 加载文件
        profile = SoulProfile()
        for filename in SOUL_FILES:
            file = self._load_soul_file(name, filename)
            if file:
                if filename == "soul.md":
                    profile.soul_md = file
                elif filename == "persona.md":
                    profile.persona_md = file
                elif filename == "taste.md":
                    profile.taste_md = file
                elif filename == "heartbeat.md":
                    profile.heartbeat_md = file

        # 缓存
        self._profiles_cache[name] = profile
        self.current_soul = name

        return profile

    def get_optimized_context(
        self, name: str, include_taste: bool = False, max_tokens: int = TOKEN_BUDGET_PER_REQUEST
    ) -> str:
        """
        获取Token优化的上下文提示

        这是核心功能：只注入soul和persona（约400 tokens），
        而不是加载所有配置，保证Token效率。

        Args:
            name: Soul名称
            include_taste: 是否包含taste
            max_tokens: 最大token限制

        Returns:
            str: 优化的上下文字符串
        """
        profile = self.load_soul(name)

        parts = []
        current_tokens = 0

        # 按优先级添加
        for attr, attr_name in [("soul_md", "Soul"), ("persona_md", "Persona"), ("taste_md", "Taste")]:
            if attr == "taste_md" and not include_taste:
                continue

            file = getattr(profile, attr)
            if file and file.is_active:
                if current_tokens + file.tokens <= max_tokens:
                    parts.append(file.to_markdown())
                    current_tokens += file.tokens

        return "

---

".join(parts)

    def switch_persona(self, name: str) -> SoulProfile:
        """
        切换人格

        Args:
            name: 目标Soul名称

        Returns:
            SoulProfile: 切换后的配置
        """
        profile = self.load_soul(name)
        self.current_soul = name

        # 清除缓存以确保加载最新
        if name in self._profiles_cache:
            del self._profiles_cache[name]

        return self.load_soul(name)

    def list_souls(self) -> list[str]:
        """
        列出所有Soul配置

        Returns:
            List[str]: Soul名称列表
        """
        souls = []
        for item in self.soul_dir.iterdir():
            if item.is_dir() and (item / "soul.md").exists():
                souls.append(item.name)
        return sorted(souls)

    def delete_soul(self, name: str) -> bool:
        """
        删除Soul配置

        Args:
            name: Soul名称

        Returns:
            bool: 是否删除成功
        """
        if name == self.default_soul:
            raise SoulIdentityError("不能删除默认Soul")

        soul_path = self.soul_dir / name
        if soul_path.exists():
            import shutil

            shutil.rmtree(soul_path)

            if name in self._profiles_cache:
                del self._profiles_cache[name]

            return True
        return False

    def duplicate_soul(self, source: str, target: str) -> SoulProfile:
        """
        复制Soul配置

        Args:
            source: 源Soul名称
            target: 目标Soul名称

        Returns:
            SoulProfile: 复制的配置
        """
        source_profile = self.load_soul(source)

        content = {}
        for attr, filename in [
            ("soul_md", "soul.md"),
            ("persona_md", "persona.md"),
            ("taste_md", "taste.md"),
            ("heartbeat_md", "heartbeat.md"),
        ]:
            file = getattr(source_profile, attr)
            if file:
                content[filename.replace(".md", "")] = file.content

        return self.create_soul(target, content)

    def get_soul_info(self, name: str) -> dict[str, Any]:
        """
        获取Soul信息摘要

        Args:
            name: Soul名称

        Returns:
            Dict: Soul信息
        """
        profile = self.load_soul(name)

        return {
            "name": name,
            "is_complete": profile.is_complete,
            "total_tokens": profile.total_tokens,
            "files": {
                "soul": profile.soul_md is not None,
                "persona": profile.persona_md is not None,
                "taste": profile.taste_md is not None,
                "heartbeat": profile.heartbeat_md is not None,
            },
            "last_modified": {
                attr: getattr(profile, attr).last_modified.isoformat() if getattr(profile, attr) else None
                for attr in ["soul_md", "persona_md", "taste_md", "heartbeat_md"]
            },
        }

    def _save_metadata(self, name: str, profile: SoulProfile):
        """保存元数据"""
        meta_path = self.soul_dir / name / ".metadata.json"

        meta = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "is_complete": profile.is_complete,
            "total_tokens": profile.total_tokens,
        }

        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def export_soul(self, name: str, output_path: str) -> str:
        """
        导出Soul配置为ZIP文件

        Args:
            name: Soul名称
            output_path: 输出路径

        Returns:
            str: 导出文件路径
        """
        import zipfile

        output = Path(output_path)
        soul_path = self.soul_dir / name

        if not soul_path.exists():
            raise SoulNotFoundError(f"Soul '{name}' 不存在")

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in soul_path.rglob("*.md"):
                zf.write(file, file.relative_to(soul_path.parent))

        return str(output)

    def import_soul(self, zip_path: str, name: str | None = None) -> str:
        """
        导入Soul配置

        Args:
            zip_path: ZIP文件路径
            name: 可选的Soul名称，默认使用ZIP内的名称

        Returns:
            str: 导入的Soul名称
        """
        import zipfile
        from io import BytesIO

        zip_file = Path(zip_path)
        if not zip_file.exists():
            raise FileNotFoundError(f"文件不存在: {zip_path}")

        soul_name = name

        with zipfile.ZipFile(zip_file, "r") as zf:
            # 读取文件列表
            file_list = zf.namelist()

            # 确定Soul名称
            if soul_name is None:
                # 从目录结构中提取
                for name in file_list:
                    parts = Path(name).parts
                    if len(parts) > 1 and parts[0].endswith(".md"):
                        soul_name = parts[0].replace(".md", "")
                        break
                if not soul_name:
                    soul_name = zip_file.stem

            # 解压到目录
            soul_path = self.soul_dir / soul_name
            soul_path.mkdir(parents=True, exist_ok=True)

            for file_info in zf.filelist:
                if file_info.filename.endswith(".md"):
                    content = zf.read(file_info.filename)
                    file_path = soul_path / Path(file_info.filename).name
                    file_path.write_bytes(content)

        return soul_name

    def render_for_llm(self, name: str, system_prefix: str = "你是一个AI助手。") -> list[dict[str, str]]:
        """
        渲染适合LLM的消息格式

        Args:
            name: Soul名称
            system_prefix: 系统前缀

        Returns:
            List[Dict]: 消息列表
        """
        context = self.get_optimized_context(name)

        return [{"role": "system", "content": f"{system_prefix}

{context}"}]

# ============================================================================
# 快捷函数
# ============================================================================

def create_default_manager() -> SoulIdentityManager:
    """创建默认的Soul身份管理器"""
    return SoulIdentityManager()

def quick_soul(soul_name: str) -> str:
    """
    快速获取Soul上下文

    Args:
        soul_name: Soul名称

    Returns:
        str: 优化的上下文字符串
    """
    manager = create_default_manager()
    return manager.get_optimized_context(soul_name)

# ============================================================================
# 示例和使用
# ============================================================================

if __name__ == "__main__":
    # 示例用法
    logger.info("=" * 60))
    # print("AUTO-EVO-AI V0.1 - Soul Identity Module")
    logger.info("=" * 60))

    # 创建管理器
    manager = SoulIdentityManager()

    # 列出所有Soul
    logger.info(f"
已配置的Soul: {manager.list_souls()}"))

    # 获取默认Soul信息
    default_info = manager.get_soul_info("default")
    logger.info(f"
默认Soul信息:"))
    logger.info(f"  - 完整配置: {default_info['is_complete']}"))
    logger.info(f"  - Token数量: {default_info['total_tokens']}"))

    # 获取优化的上下文
    context = manager.get_optimized_context("default")
    logger.info(f"
优化上下文预览 (前500字符):"))
    logger.info("-" * 40))
    logger.info(context[:500] + "..."))

    # 创建自定义Soul示例
    logger.info("
" + "-" * 40))
    logger.info("创建自定义Soul示例:"))

    custom_soul = manager.create_soul(
        "coding_assistant",
        {
            "soul": """# Soul - 编程助手灵魂

## 身份定位
我是一个专注于编程和代码开发的AI助手。

## 核心价值观
1. **代码优先** - 高质量、可维护的代码
2. **最佳实践** - 遵循业界最佳实践
3. **清晰注释** - 代码即文档
4. **持续优化** - 不断改进代码质量
""",
            "persona": """# Persona - 编程专家人格

## 专业能力
- 多语言编程（Python, JavaScript, TypeScript, Go等）
- 代码审查和优化
- 架构设计和模式
- 调试和问题排查

## 沟通风格
- 直接给出代码解决方案
- 解释关键设计决策
- 提供完整可运行的代码
- 使用技术术语但保持清晰
""",
            "taste": """# Taste - 编程品味

## 代码风格
- 遵循PEP 8 / StandardJS等规范
- 使用类型提示增加可读性
- 适当的注释说明复杂逻辑
- 模块化和可复用设计

## 回答偏好
- 先给结论，后解释
- 代码块要完整可运行
- 提供测试用例
- 说明复杂度
""",
            "heartbeat": {"enabled": True, "interval": 300, "notify_on_error": True},
        },
    )

    logger.info(f"✅ 创建自定义Soul: coding_assistant"))

    # 切换到自定义Soul
    context = manager.get_optimized_context("coding_assistant")
    logger.info(f"
自定义Soul上下文:"))
    logger.info("-" * 40))
    logger.info(context[:300] + "..."))

    logger.info("
" + "=" * 60))
    logger.info("Soul Identity Module 测试完成!"))
    logger.info("=" * 60))

    async def execute(self, action: str = "status", params: dict = None) -> dict:
        """执行入口 - 路由到soul_identity业务方法"""
        params = params or {}
        self.trace("soul_identity.execute", "start", action=action)
        self.metrics_collector.counter("soul_identity.execute.total", 1)
        try:
            a = (action or "status").lower().strip()
            if a == "to_markdown":
                result = self.to_markdown(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "to_markdown"
                self.metrics_collector.counter("soul_identity.execute.to_markdown", 1)
                return result
            if a == "token_count":
                result = self.token_count(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "token_count"
                self.metrics_collector.counter("soul_identity.execute.token_count", 1)
                return result
            if a == "total_tokens":
                result = self.total_tokens(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "total_tokens"
                self.metrics_collector.counter("soul_identity.execute.total_tokens", 1)
                return result
            if a == "is_complete":
                result = self.is_complete(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "is_complete"
                self.metrics_collector.counter("soul_identity.execute.is_complete", 1)
                return result
            if a == "get_active_files":
                result = self.get_active_files(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "get_active_files"
                self.metrics_collector.counter("soul_identity.execute.get_active_files", 1)
                return result
            if a == "_init_default_soul":
                result = self._init_default_soul(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_init_default_soul"
                self.metrics_collector.counter("soul_identity.execute._init_default_soul", 1)
                return result
            if a == "_estimate_tokens":
                result = self._estimate_tokens(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_estimate_tokens"
                self.metrics_collector.counter("soul_identity.execute._estimate_tokens", 1)
                return result
            if a == "_load_soul_file":
                result = self._load_soul_file(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_load_soul_file"
                self.metrics_collector.counter("soul_identity.execute._load_soul_file", 1)
                return result
            if a == "_dict_to_heartbeat":
                result = self._dict_to_heartbeat(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_dict_to_heartbeat"
                self.metrics_collector.counter("soul_identity.execute._dict_to_heartbeat", 1)
                return result
            if a == "load_soul":
                result = self.load_soul(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "load_soul"
                self.metrics_collector.counter("soul_identity.execute.load_soul", 1)
                return result
            if a == "switch_persona":
                result = self.switch_persona(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "switch_persona"
                self.metrics_collector.counter("soul_identity.execute.switch_persona", 1)
                return result
            if a == "list_souls":
                result = self.list_souls(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "list_souls"
                self.metrics_collector.counter("soul_identity.execute.list_souls", 1)
                return result
            if a == "delete_soul":
                result = self.delete_soul(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "delete_soul"
                self.metrics_collector.counter("soul_identity.execute.delete_soul", 1)
                return result
            if a == "duplicate_soul":
                result = self.duplicate_soul(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "duplicate_soul"
                self.metrics_collector.counter("soul_identity.execute.duplicate_soul", 1)
                return result
            if a == "get_soul_info":
                result = self.get_soul_info(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "get_soul_info"
                self.metrics_collector.counter("soul_identity.execute.get_soul_info", 1)
                return result
            if a == "_save_metadata":
                result = self._save_metadata(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "_save_metadata"
                self.metrics_collector.counter("soul_identity.execute._save_metadata", 1)
                return result
            if a == "export_soul":
                result = self.export_soul(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "export_soul"
                self.metrics_collector.counter("soul_identity.execute.export_soul", 1)
                return result
            if a == "import_soul":
                result = self.import_soul(**{k: v for k, v in params.items() if k in [p for p in ""]})
                if not isinstance(result, dict):
                    result = {"result": str(result)[:500]}
                result["action"] = "import_soul"
                self.metrics_collector.counter("soul_identity.execute.import_soul", 1)
                return result
            if a in ("status", "info", "stats", "health"):
                return {"success": True, "status": "running", "module": "soul_identity", "health": self.health_check()}
            if a == "help":
                return {
                    "actions": [
                        "to_markdown",
                        "token_count",
                        "total_tokens",
                        "is_complete",
                        "get_active_files",
                        "_init_default_soul",
                        "_estimate_tokens",
                        "_load_soul_file",
                        "_dict_to_heartbeat",
                        "load_soul",
                        "switch_persona",
                        "list_souls",
                        "delete_soul",
                        "duplicate_soul",
                        "get_soul_info",
                    ],
                    "module": "soul_identity",
                }
            return {
                "success": True,
                "action": a,
                "module": "soul_identity",
                "available": [
                    "to_markdown",
                    "token_count",
                    "total_tokens",
                    "is_complete",
                    "get_active_files",
                    "_init_default_soul",
                    "_estimate_tokens",
                    "_load_soul_file",
                    "_dict_to_heartbeat",
                    "load_soul",
                ],
            }
        except Exception as e:
            self.metrics_collector.counter("soul_identity.execute.error", 1)
            return {"success": False, "error": str(e), "action": action}

def shutdown(self) -> dict:
    self.trace("soul_identity.shutdown", "start")
    self.status = "stopped"
    self.trace("soul_identity.shutdown", "end")
    return {"success": True, "module": "soul_identity"}

def health_check(self) -> dict:
    return {"status": "healthy", "module": "soul_identity", "version": getattr(self, "version", "1.0.0")}

def initialize(self) -> dict:
    self.trace("soul_identity.initialize", "start")
    self.metrics_collector.gauge("soul_identity.initialized", 1)
    self.audit("初始化soul_identity", level="info")
    self.trace("soul_identity.initialize", "end")
    return {"success": True, "module": "soul_identity"}

module_class = SoulIdentityManager
