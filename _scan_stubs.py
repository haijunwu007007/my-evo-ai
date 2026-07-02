"""快速扫描空壳路由文件"""
import os

base = r'D:\AUTO-EVO-AI-V0.1\api\routes'
results = []

for f in sorted(os.listdir(base)):
    if not f.startswith('routes_') or not f.endswith('.py') or f == '__init__.py':
        continue
    fp = os.path.join(base, f)
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            content = fh.read()
        lines = content.count('\n') + 1
        # 检查是否只有 1-2 个端点 + 简单返回
        has_async_def = content.count('async def')
        import_lines = [l for l in content.split('\n') if l.strip().startswith('import') or l.strip().startswith('from')]
        # 检测空壳特征
        is_stub = lines < 50 and has_async_def <= 3
        is_mock = 'return {"success": True}' in content or 'return JSONResponse({"success":True' in content.replace(' ', '')
        has_mock_comment = '# stub' in content.lower() or '# todo' in content.lower()
        
        results.append((f, lines, has_async_def, len(import_lines), is_stub, is_mock))
    except Exception:
        pass

# 按行数排序，显示最薄的文件
results.sort(key=lambda x: x[1])

print(f"{'文件':35s} {'行数':>4s} {'端点':>4s} {'导入':>4s} {'薄？':>4s} {'Mock？':>5s}")
print('-' * 58)
stub_count = 0
for f, lines, defs, imps, is_stub, is_mock in results:
    thin = 'Y' if is_stub else ''
    mock = 'Y' if is_mock else ''
    flag = ' ***' if (is_stub and is_mock) else ''
    if is_stub or is_mock:
        stub_count += 1
        print(f"{f:35s} {lines:4d} {defs:4d} {imps:4d} {thin:>4s} {mock:>5s}{flag}")
        
print(f'\n共 {len(results)} 个路由文件，{stub_count} 个疑似空壳')
