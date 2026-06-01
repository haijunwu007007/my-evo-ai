#!/usr/bin/env python3
"""E2E API 集成测试 — 启动服务器 → 验证端点 → 关闭"""
import subprocess, urllib.request, json, sys, time, os, signal

def test():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Start server
    proc = subprocess.Popen(
        [sys.executable, 'api_server.py'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    results = []
    def check(name, url, expect_status=200):
        try:
            r = urllib.request.urlopen(f'http://127.0.0.1:8765{url}', timeout=10)
            ok = r.status == expect_status
            results.append((name, 'PASS' if ok else f'FAIL(status={r.status})'))
            if not ok:
                print(f'  FAIL {name}: expected {expect_status}, got {r.status}')
        except Exception as e:
            results.append((name, f'FAIL({str(e)[:50]})'))
    
    # Wait for server
    for i in range(30):
        try:
            urllib.request.urlopen('http://127.0.0.1:8765/', timeout=2)
            break
        except Exception:
            time.sleep(1)
    
    # 2. Test endpoints
    check('Root', '/')
    check('API Status', '/api/v1/status')
    check('Legacy Status', '/api/status')
    check('Auth Config', '/api/v1/auth/config')
    check('Modules', '/api/v1/modules')
    check('Scheduler', '/api/v1/scheduler/status')
    check('Coordinator', '/api/v1/coordinator/status')
    check('Diagnosis', '/api/v1/diagnosis/system')
    check('Metrics', '/metrics')
    check('Dashboard', '/dashboard', 200)
    check('Frontend Assets', '/favicon.ico', 200)
    
    # 3. Stop server
    proc.terminate()
    proc.wait(timeout=5)
    
    # 4. Report
    passed = sum(1 for _, s in results if s == 'PASS')
    failed = sum(1 for _, s in results if 'FAIL' in s)
    print(f'\nE2E Results: {passed}/{passed+failed} passed')
    for name, status in results:
        print(f'  {name:25s} {status}')
    
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    test()
