"""核心功能测试 — LLM/Agent/文件操作/多语言"""
import pytest, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── LLM 聊天 ──────────────────────────────
class TestLLMChat:
    def test_providers_config(self):
        from api.routes_llm_chat import PROVIDERS
        assert len(PROVIDERS) >= 13, f"需要13+提供商，当前: {len(PROVIDERS)}"
        required = {"openai", "deepseek", "qwen", "glm", "kimi"}
        assert required.issubset(PROVIDERS.keys()), f"缺少必备提供商: {required - PROVIDERS.keys()}"
        print(f"✅ 全部提供商: {list(PROVIDERS.keys())}")

    def test_smart_chat_rules(self):
        from api.routes_smart_chat import SmartChatRequest
        req = SmartChatRequest(message="你会什么", lang="zh-CN")
        assert req.message == "你会什么"
        assert req.lang == "zh-CN"
        print("✅ SmartChatRequest 正常")

# ── 智能体 ────────────────────────────────
class TestAgents:
    def test_agent_team(self):
        from api.routes_agents import AGENT_TEAM
        assert len(AGENT_TEAM) == 6, f"需要6个智能体，当前: {len(AGENT_TEAM)}"
        ids = [a["id"] for a in AGENT_TEAM]
        assert "athena" in ids
        print(f"✅ 智能体团队: {ids}")

    def test_create_room_validation(self):
        from api.routes_agents import RoomCreate
        r = RoomCreate(task="测试讨论")
        assert r.task == "测试讨论"
        print("✅ RoomCreate 正常")

# ── 文件操作 ──────────────────────────────
class TestFileOps:
    def test_excel_read_write(self):
        from modules.file_ops import excel_write, excel_read
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        test_path = os.path.join(output_dir, "_test.xlsx")
        r = excel_write(test_path, [["A", "B"], [1, 2]])
        assert "✅" in r, f"写入失败: {r}"
        r2 = excel_read(test_path)
        assert "Excel" in r2, f"读取失败: {r2}"
        os.remove(test_path)
        print("✅ Excel 读写正常")

    def test_word_create(self):
        from modules.file_ops import word_create
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        test_path = os.path.join(output_dir, "_test.docx")
        r = word_create(test_path, "Test", "Hello World")
        assert "✅" in r, f"Word生成失败: {r}"
        os.remove(test_path)
        print("✅ Word 生成正常")

# ── 多语言 ────────────────────────────────
class TestI18n:
    def test_i18n_api(self):
        from api.routes_i18n import I18N_BACKEND
        assert len(I18N_BACKEND) >= 4, f"需要4+语言，当前: {len(I18N_BACKEND)}"
        core = {"zh-CN", "en", "ja", "ko"}
        missing = core - set(I18N_BACKEND.keys())
        assert not missing, f"缺少语言: {missing}"
        # 前端另有9种语言在 i18n.js
        print(f"✅ 后端多语言数: {len(I18N_BACKEND)} (前端另有9种在 i18n.js)")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
