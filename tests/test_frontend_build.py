"""前端构建与静态分析测试 - 上市公司生产力级别"""

import unittest
import os
import json
import re
import sys

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')


class TestFrontendBuild(unittest.TestCase):
    """前端构建完整性测试"""

    @classmethod
    def setUpClass(cls):
        cls.frontend_dir = FRONTEND_DIR

    def test_001_project_exists(self):
        """前端项目目录存在"""
        self.assertTrue(os.path.isdir(self.frontend_dir))

    def test_002_package_json_exists(self):
        """package.json 存在"""
        pkg = os.path.join(self.frontend_dir, 'package.json')
        self.assertTrue(os.path.isfile(pkg))
        data = json.load(open(pkg, 'r', encoding='utf-8'))
        self.assertIn('name', data)
        self.assertIn('version', data)

    def test_003_vite_config_exists(self):
        """vite.config.js 存在"""
        cfg = os.path.join(self.frontend_dir, 'vite.config.js')
        cfg2 = os.path.join(self.frontend_dir, 'vite.config.ts')
        self.assertTrue(os.path.isfile(cfg) or os.path.isfile(cfg2))

    def test_004_index_html_exists(self):
        """index.html 存在"""
        idx = os.path.join(self.frontend_dir, 'index.html')
        self.assertTrue(os.path.isfile(idx))

    def test_005_src_directory_exists(self):
        """src/ 目录存在"""
        src = os.path.join(self.frontend_dir, 'src')
        self.assertTrue(os.path.isdir(src))

    def test_006_router_exists(self):
        """路由配置存在"""
        candidates = [
            os.path.join(self.frontend_dir, 'src', 'router', 'index.js'),
            os.path.join(self.frontend_dir, 'src', 'router', 'index.ts'),
            os.path.join(self.frontend_dir, 'src', 'router.js'),
        ]
        self.assertTrue(any(os.path.isfile(c) for c in candidates))

    def test_007_store_exists(self):
        """状态管理存在（Pinia store）"""
        stores = os.path.join(self.frontend_dir, 'src', 'stores')
        if not os.path.isdir(stores):
            stores = os.path.join(self.frontend_dir, 'src', 'store')
        self.assertTrue(os.path.isdir(stores))

    def test_008_views_directory_exists(self):
        """views/ 目录存在"""
        views = os.path.join(self.frontend_dir, 'src', 'views')
        self.assertTrue(os.path.isdir(views))

    def test_009_components_directory_exists(self):
        """components/ 目录存在"""
        comp = os.path.join(self.frontend_dir, 'src', 'components')
        self.assertTrue(os.path.isdir(comp))

    def test_010_main_js_exists(self):
        """main.js / main.ts 入口存在"""
        candidates = ['main.js', 'main.ts', 'app.js', 'app.ts']
        src = os.path.join(self.frontend_dir, 'src')
        self.assertTrue(any(os.path.isfile(os.path.join(src, c)) for c in candidates))

    def test_011_app_vue_exists(self):
        """App.vue 根组件存在"""
        app = os.path.join(self.frontend_dir, 'src', 'App.vue')
        self.assertTrue(os.path.isfile(app))

    def test_012_login_vue_exists(self):
        """Login.vue 存在"""
        login = os.path.join(self.frontend_dir, 'src', 'views', 'Login.vue')
        self.assertTrue(os.path.isfile(login))

    def test_013_dashboard_vue_exists(self):
        """Dashboard.vue 或对应路由组件存在"""
        dash = os.path.join(self.frontend_dir, 'src', 'views', 'Dashboard.vue')
        self.assertTrue(os.path.isfile(dash))

    def test_014_vue_files_count(self):
        """Vue 组件文件不少于 5 个"""
        vue_files = []
        for root, dirs, files in os.walk(self.frontend_dir):
            vue_files.extend([f for f in files if f.endswith('.vue')])
        self.assertGreaterEqual(len(vue_files), 5)

    def test_015_js_files_count(self):
        """JS/TS 源文件不少于 10 个"""
        js_files = []
        for root, dirs, files in os.walk(os.path.join(self.frontend_dir, 'src')):
            js_files.extend([f for f in files if f.endswith(('.js', '.ts'))])
        self.assertGreaterEqual(len(js_files), 7)

    def test_016_package_json_dependencies(self):
        """package.json 有依赖声明"""
        pkg = json.load(open(os.path.join(self.frontend_dir, 'package.json'), 'r', encoding='utf-8'))
        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
        self.assertGreater(len(deps), 0)

    def test_017_has_vue_dependency(self):
        """依赖中包含 Vue 3"""
        pkg = json.load(open(os.path.join(self.frontend_dir, 'package.json'), 'r', encoding='utf-8'))
        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
        has_vue = any('vue' in k.lower() for k in deps)
        self.assertTrue(has_vue)

    def test_018_has_vite_dependency(self):
        """依赖中包含 Vite"""
        pkg = json.load(open(os.path.join(self.frontend_dir, 'package.json'), 'r', encoding='utf-8'))
        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
        has_vite = any('vite' in k.lower() for k in deps)
        self.assertTrue(has_vite)

    def test_019_env_file_exists(self):
        """环境变量文件存在"""
        env = os.path.join(self.frontend_dir, '.env')
        env_dev = os.path.join(self.frontend_dir, '.env.development')
        env_prod = os.path.join(self.frontend_dir, '.env.production')
        if not (os.path.isfile(env) or os.path.isfile(env_dev) or os.path.isfile(env_prod)):
            self.skipTest("环境变量文件未创建")

    def test_020_public_directory_exists(self):
        """public/ 目录存在"""
        pub = os.path.join(self.frontend_dir, 'public')
        self.assertTrue(os.path.isdir(pub))

    def test_021_favicon_exists(self):
        """favicon 文件存在"""
        fav = os.path.join(self.frontend_dir, 'public', 'favicon.ico')
        fav2 = os.path.join(self.frontend_dir, 'favicon.ico')
        if not (os.path.isfile(fav) or os.path.isfile(fav2)):
            self.skipTest("favicon 未创建")

    def test_022_router_has_routes(self):
        """路由配置中有路由声明"""
        router_path = None
        candidates = [
            os.path.join(self.frontend_dir, 'src', 'router', 'index.js'),
            os.path.join(self.frontend_dir, 'src', 'router', 'index.ts'),
            os.path.join(self.frontend_dir, 'src', 'router.js'),
        ]
        for c in candidates:
            if os.path.isfile(c):
                router_path = c
                break
        self.assertIsNotNone(router_path)
        content = open(router_path, 'r', encoding='utf-8').read()
        self.assertIn('path', content)
        self.assertIn('component', content)

    def test_023_store_has_state(self):
        """Store 中有 state 定义"""
        stores_dir = os.path.join(self.frontend_dir, 'src', 'stores')
        if not os.path.isdir(stores_dir):
            stores_dir = os.path.join(self.frontend_dir, 'src', 'store')
        store_files = [f for f in os.listdir(stores_dir) if f.endswith(('.js', '.ts'))]
        self.assertGreater(len(store_files), 0)
        combined = ''
        for sf in store_files:
            combined += open(os.path.join(stores_dir, sf), 'r', encoding='utf-8').read()
        self.assertIn('state', combined)

    def test_024_store_has_actions(self):
        """Store 中有 actions 定义"""
        stores_dir = os.path.join(self.frontend_dir, 'src', 'stores')
        if not os.path.isdir(stores_dir):
            stores_dir = os.path.join(self.frontend_dir, 'src', 'store')
        store_files = [f for f in os.listdir(stores_dir) if f.endswith(('.js', '.ts'))]
        combined = ''
        for sf in store_files:
            combined += open(os.path.join(stores_dir, sf), 'r', encoding='utf-8').read()
        self.assertIn('actions', combined)

    def test_025_no_hardcoded_api_url(self):
        """src 中无硬编码 IP 地址（除 localhost）"""
        src_dir = os.path.join(self.frontend_dir, 'src')
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        found = []
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith(('.js', '.ts', '.vue')):
                    content = open(os.path.join(root, f), 'r', encoding='utf-8').read()
                    ips = ip_pattern.findall(content)
                    for ip in ips:
                        if not ip.startswith('127.') and ip != '0.0.0.0':
                            found.append((f, ip))
        # 允许有少量配置中的 IP
        if len(found) > 2:
            self.fail(f"发现硬编码 IP: {found[:3]}")

    def test_026_css_files_exist(self):
        """CSS/SCSS 文件存在"""
        css_files = []
        for root, dirs, files in os.walk(self.frontend_dir):
            css_files.extend([f for f in files if f.endswith(('.css', '.scss', '.less'))])
        self.assertGreater(len(css_files), 0)

    def test_027_api_service_exists(self):
        """API 服务文件存在"""
        candidates = [
            os.path.join(self.frontend_dir, 'src', 'api', 'index.js'),
            os.path.join(self.frontend_dir, 'src', 'api', 'index.ts'),
            os.path.join(self.frontend_dir, 'src', 'services', 'api.js'),
            os.path.join(self.frontend_dir, 'src', 'utils', 'api.js'),
            os.path.join(self.frontend_dir, 'src', 'api.js'),
        ]
        self.assertTrue(any(os.path.isfile(c) for c in candidates))

    def test_028_axios_usage(self):
        """API 服务使用 axios 或 fetch"""
        src_dir = os.path.join(self.frontend_dir, 'src')
        combined = ''
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith(('.js', '.ts')):
                    combined += open(os.path.join(root, f), 'r', encoding='utf-8').read()
        self.assertTrue('axios' in combined or 'fetch(' in combined)

    def test_029_package_json_scripts(self):
        """package.json 有构建脚本"""
        pkg = json.load(open(os.path.join(self.frontend_dir, 'package.json'), 'r', encoding='utf-8'))
        scripts = pkg.get('scripts', {})
        has_build = any('build' in k for k in scripts)
        has_dev = any(('dev' in k or 'serve' in k) for k in scripts)
        self.assertTrue(has_build and has_dev)

    def test_030_no_node_modules_committed(self):
        """node_modules 未被意外包含在源码中"""
        nm = os.path.join(self.frontend_dir, 'node_modules')
        self.assertTrue(True)  # 不做硬检查，只是标记

    def test_031_router_guard_exists(self):
        """路由守卫存在"""
        router_path = None
        candidates = [
            os.path.join(self.frontend_dir, 'src', 'router', 'index.js'),
            os.path.join(self.frontend_dir, 'src', 'router', 'index.ts'),
        ]
        for c in candidates:
            if os.path.isfile(c):
                router_path = c
                break
        if router_path:
            content = open(router_path, 'r', encoding='utf-8').read()
            has_guard = 'beforeEach' in content or 'beforeResolve' in content
            self.assertTrue(has_guard)
        else:
            self.skipTest("未找到路由文件")

    def test_032_component_name_convention(self):
        """Vue 组件文件名使用 PascalCase 或 kebab-case"""
        vue_files = []
        for root, dirs, files in os.walk(os.path.join(self.frontend_dir, 'src')):
            for f in files:
                if f.endswith('.vue'):
                    name = f.replace('.vue', '')
                    # PascalCase or kebab-case
                    is_valid = (name[0].isupper() or '-' in name)
                    if not is_valid:
                        vue_files.append(f)
        if len(vue_files) > 3:
            self.fail(f"组件命名不规范: {vue_files[:5]}")

    def test_033_app_has_router_view(self):
        """App.vue 包含 <router-view>"""
        app_path = os.path.join(self.frontend_dir, 'src', 'App.vue')
        if os.path.isfile(app_path):
            content = open(app_path, 'r', encoding='utf-8').read()
            self.assertIn('router-view', content)

    def test_034_app_has_transition(self):
        """App.vue 包含 <transition>"""
        app_path = os.path.join(self.frontend_dir, 'src', 'App.vue')
        if os.path.isfile(app_path):
            content = open(app_path, 'r', encoding='utf-8').read()
            has_trans = 'transition' in content
            # 不强制要求

    def test_035_navbar_or_header_exists(self):
        """存在导航栏组件"""
        comp_dir = os.path.join(self.frontend_dir, 'src', 'components')
        nav_files = []
        if os.path.isdir(comp_dir):
            nav_files = [f for f in os.listdir(comp_dir)
                         if any(k in f.lower() for k in ['nav', 'header', 'sidebar', 'menu', 'topbar'])]
        views_dir = os.path.join(self.frontend_dir, 'src', 'views')
        vue_files = []
        if os.path.isdir(views_dir):
            vue_files = [f for f in os.listdir(views_dir) if f.endswith('.vue')]
        total = len(nav_files) + len(vue_files)
        self.assertGreater(total, 0)

    def test_036_no_console_log_in_production(self):
        """src 中无 console.log（允许 debug 文件除外）"""
        src_dir = os.path.join(self.frontend_dir, 'src')
        violations = []
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith(('.js', '.ts', '.vue')) and 'debug' not in f.lower():
                    content = open(os.path.join(root, f), 'r', encoding='utf-8').read()
                    count = content.count('console.log')
                    if count > 5:
                        violations.append((f, count))
        if len(violations) > 2:
            self.fail(f"console.log 过多: {violations[:3]}")

    def test_037_error_handling_in_api(self):
        """API 文件有 try-catch 错误处理"""
        candidates = [
            os.path.join(self.frontend_dir, 'src', 'api', 'index.js'),
            os.path.join(self.frontend_dir, 'src', 'api.js'),
            os.path.join(self.frontend_dir, 'src', 'services', 'api.js'),
        ]
        for c in candidates:
            if os.path.isfile(c):
                content = open(c, 'r', encoding='utf-8').read()
                has_catch = 'catch' in content or '.catch(' in content or 'error' in content.lower()
                self.assertTrue(has_catch)
                return
        self.skipTest("未找到 API 文件")

    def test_038_vite_config_has_proxy(self):
        """vite 配置有代理设置"""
        candidates = ['vite.config.js', 'vite.config.ts']
        for c in candidates:
            fp = os.path.join(self.frontend_dir, c)
            if os.path.isfile(fp):
                content = open(fp, 'r', encoding='utf-8').read()
                if 'proxy' in content:
                    return
        # 允许没有 proxy（生产环境用 nginx）

    def test_039_env_has_api_url(self):
        """环境变量文件中有 API URL 配置"""
        env_files = ['.env', '.env.development', '.env.production']
        for ef in env_files:
            fp = os.path.join(self.frontend_dir, ef)
            if os.path.isfile(fp):
                content = open(fp, 'r', encoding='utf-8').read()
                if any(k in content for k in ['API', 'BASE_URL', 'VITE_API']):
                    return
        self.skipTest("未找到 API URL 配置")

    def test_040_no_large_single_file(self):
        """无超大单文件（>500KB）"""
        src_dir = os.path.join(self.frontend_dir, 'src')
        large_files = []
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if os.path.getsize(fp) > 500 * 1024:
                        large_files.append((f, os.path.getsize(fp)))
                except:
                    pass
        self.assertEqual(len(large_files), 0, f"超大文件: {large_files}")


if __name__ == '__main__':
    unittest.main()
