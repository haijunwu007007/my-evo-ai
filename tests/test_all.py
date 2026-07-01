"""AUTO-EVO-AI 核心测试套件"""
import urllib.request,ssl,json,unittest

BASE='https://autoevoai.com'
ctx=ssl.create_default_context()

class TestPublicAPI(unittest.TestCase):
    def test_1_home(self):
        r=urllib.request.urlopen(BASE,timeout=10,context=ctx)
        self.assertEqual(r.status,200)
    def test_2_chat(self):
        r=urllib.request.urlopen(BASE+'/chat.html',timeout=10,context=ctx)
        self.assertIn(b'AUTO-EVO',r.read())
    def test_3_enterprise(self):
        r=urllib.request.urlopen(BASE+'/enterprise.html',timeout=10,context=ctx)
        data=r.read()
        self.assertGreater(len(data),500000)
        self.assertIn(b'window.',data)
    def test_4_admin(self):
        r=urllib.request.urlopen(BASE+'/admin',timeout=10,context=ctx)
        self.assertIn(b'showTab',r.read())
    def test_5_billion_os(self):
        r=urllib.request.urlopen(BASE+'/billion-os.html',timeout=10,context=ctx)
        data=r.read()
        self.assertIn(b'runGenesis',data)
        self.assertIn(b'MAIN_SCRIPT_OK',data)
    def test_6_audit(self):
        r=urllib.request.urlopen(BASE+'/audit',timeout=10,context=ctx)
        self.assertIn(b'审计日志',r.read())
    def test_7_webhooks(self):
        r=urllib.request.urlopen(BASE+'/webhooks',timeout=10,context=ctx)
        self.assertIn(b'Webhook',r.read())
    def test_8_backup(self):
        r=urllib.request.urlopen(BASE+'/backup',timeout=10,context=ctx)
        self.assertIn(b'备份',r.read())
    def test_9_marketplace(self):
        r=urllib.request.urlopen(BASE+'/marketplace',timeout=10,context=ctx)
        self.assertIn(b'模块',r.read())
    def test_10_bi(self):
        r=urllib.request.urlopen(BASE+'/bi',timeout=10,context=ctx)
        self.assertIn(b'仪表盘',r.read())
    def test_11_realtime(self):
        r=urllib.request.urlopen(BASE+'/realtime',timeout=10,context=ctx)
        self.assertIn(b'实时',r.read())
    def test_12_editor(self):
        r=urllib.request.urlopen(BASE+'/editor',timeout=10,context=ctx)
        self.assertIn(b'文档',r.read())
    def test_13_install_sh(self):
        r=urllib.request.urlopen(BASE+'/install/install.sh',timeout=10,context=ctx)
        self.assertIn(b'docker',r.read())
    def test_14_docker_compose(self):
        r=urllib.request.urlopen(BASE+'/install/docker-compose.yml',timeout=10,context=ctx)
        self.assertIn(b'services',r.read())
    def test_15_sdk_python(self):
        r=urllib.request.urlopen(BASE+'/sdk/python/evoclient.py',timeout=10,context=ctx)
        self.assertIn(b'class',r.read())
    def test_16_sdk_js(self):
        r=urllib.request.urlopen(BASE+'/sdk/js/evoclient.js',timeout=10,context=ctx)
        self.assertIn(b'function',r.read())
    def test_17_version(self):
        r=urllib.request.urlopen(BASE+'/api/v1/version',timeout=10,context=ctx)
        j=json.loads(r.read())
        self.assertIn('version',j)
    def test_18_enterprise_window_exports(self):
        r=urllib.request.urlopen(BASE+'/enterprise.html',timeout=10,context=ctx)
        data=r.read().decode()
        count=len(re.findall(r'window\.\w+\s*=',data))
        self.assertGreaterEqual(count,145,f'Expected >=145 window exports, got {count}')

if __name__=='__main__':
    unittest.main(verbosity=2)
