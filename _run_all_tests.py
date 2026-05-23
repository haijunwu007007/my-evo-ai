import sys, os, subprocess

root = r'D:\AUTO-EVO-AI-V0.1'
os.chdir(root)
sys.path.insert(0, root)

results = []
for tf in sorted(os.listdir(os.path.join(root, 'tests'))):
    if not tf.startswith('test_') or not tf.endswith('.py'):
        continue
    try:
        r = subprocess.run(
            [sys.executable, '-m', 'pytest', os.path.join('tests', tf), '-q', '--no-header', '--tb=short'],
            capture_output=True, text=True, timeout=30, cwd=root
        )
        results.append((tf, r.returncode, r.stdout.strip().split('\n')[-1:] if r.stdout else [], r.stderr[:200]))
    except subprocess.TimeoutExpired:
        results.append((tf, -1, ['TIMEOUT'], ''))
    except Exception as e:
        results.append((tf, -2, [str(e)], ''))

print('=== 测试结果 ===')
ok = fail = 0
for name, rc, out, err in results:
    if rc == 0:
        print(f'  PASS {name}: {out[0] if out else "ok"}')
        ok += 1
    elif rc == -1:
        print(f'  FAIL {name}: TIMEOUT')
        fail += 1
    else:
        print(f'  FAIL {name}: rc={rc} | {out[0][:120] if out else err[:120]}')
        fail += 1

print(f'\n=> {ok} passed, {fail} failed')
