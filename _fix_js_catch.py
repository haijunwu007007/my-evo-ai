import re

with open('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat_engine.js', 'r', encoding='utf-8') as f:
    c = f.read()

old_pat = r'catch\(e\)\{if\(_sse_retries<3&&e\.name!="AbortError"\)\{updateThinking\(chr\(128260\),"重连中\.\.\.\n";await new Promise\(r=>setTimeout\(r,2000\)\);continue\}'

count = len(re.findall(old_pat, c))
print(f'匹配数: {count}')

# more precise: find the exact string without regex
target = '}catch(e){if(_sse_retries<3&&e.name!="AbortError"){updateThinking(chr(128260),"重连中...");await new Promise(r=>setTimeout(r,2000));continue}'
count2 = c.count(target)
print(f'精确匹配数: {count2}')

if count2 > 0:
    new_c = c.replace(target, '}catch(e){/*ignore*/}')
    # verify
    remaining = new_c.count(target)
    print(f'替换后剩余: {remaining}')
    with open('D:\\AUTO-EVO-AI-V0.1\\frontend\\chat_engine.js', 'w', encoding='utf-8') as f:
        f.write(new_c)
    print('OK - 文件已更新')
else:
    print('未找到精确匹配，尝试逐步匹配...')
    # print first 200 chars for debugging
    idx = c.find('_sse_retries<3')
    if idx >= 0:
        start = max(0, idx - 50)
        end = min(len(c), idx + 150)
        print(f'上下文: |{c[start:end]}|')
