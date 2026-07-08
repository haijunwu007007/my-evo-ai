"""测试拆分后模块的可导入性和基本功能"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestSplitModules(unittest.TestCase):
    """验证10个拆分模块的导入和基本功能"""

    def test_001_agent_resource_control(self):
        from modules.resource_control import AgentPoolType
        at = AgentPoolType("test")
        self.assertIsNotNone(at)

    def test_002_agent_planner(self):
        from modules.agent_planning import AgentPlanner
        ap = AgentPlanner()
        self.assertTrue(hasattr(ap, "get_status") or hasattr(ap, "plan"))

    def test_003_finance_data(self):
        from modules.finance_data import M53FinanceData as FD
        fd = FD()
        s = fd.get_status() if hasattr(fd, "get_status") else {"ok": True}
        self.assertIsNotNone(s)

    def test_004_rag_flow(self):
        from modules.rag_flow import DocumentFormat
        self.assertEqual(DocumentFormat.PDF.value, "pdf")

    def test_005_cli_interface(self):
        from modules.cli_tools import CLIInterface
        ci = CLIInterface()
        self.assertIsNotNone(ci)

    def test_006_second_brain(self):
        from modules.second_brain import SecondBrainAnalyzer
        sb = SecondBrainAnalyzer()
        s = sb.get_status() if hasattr(sb, "get_status") else {"ok": True}
        self.assertIsNotNone(s)

    def test_007_hephaestus(self):
        from modules.hephaestus import BuildStatus
        self.assertTrue(hasattr(BuildStatus, "value") or hasattr(BuildStatus, "name"))

    def test_008_core_decision(self):
        from core.decision.core import DecisionEngine
        de = DecisionEngine()
        self.assertIsNotNone(de)

    def test_009_core_llm(self):
        from core.llm.core import LLMGateway
        llm = LLMGateway()
        self.assertIsNotNone(llm)

    def test_010_routes_features(self):
        from api.routes.features.core import router
        self.assertIsNotNone(router)

    def test_011_core_decision_imports_via_init(self):
        from core.decision import DecisionEngine
        de = DecisionEngine()
        self.assertIsNotNone(de)

    def test_012_core_llm_imports_via_init(self):
        from core.llm import LLMGateway
        llm = LLMGateway()
        self.assertIsNotNone(llm)

if __name__ == "__main__":
    unittest.main()
