"""检查chat.html语法"""
import re
html = open('D:/AUTO-EVO-AI-V0.1/frontend/chat.html', encoding='utf-8').read()

# 统计消息渲染位置
addmsg = len(re.findall(r'function addMsg\(', html))
streaming = len(re.findall(r'full\.replace', html))
bubbles = len(re.findall(r'msg-bubble', html))
answers = []
for m in re.finditer(r'addMsg\(.*?,.*?\'bot\'\)', html):
    answers.append(m.group()[:80])

print(f"addMsg函数: {addmsg}")
print(f"流式渲染: {streaming}")
print(f"msg-bubble出现: {bubbles}")

# 检查_TOOL_KEYWORDS数组
idx = html.find('var _TOOL_KEYWORDS')
end = html.find('function quickTool', idx)
arr = html[idx:end]

# 找所有不在字符串中的:
# 简单方法：找数组最末尾
last_line = arr.strip().split('\n')[-1]
print(f"\n_TOOL_KEYWORDS最后一行: {last_line[:80]}")
if ':' in last_line and '"' not in last_line.split(':')[0]:
    print("  ⚠️ 发现可能的对象语法混入数组！")

# 检查是否缺少逗号导致的两个字符串相连
pairs = re.findall(r'"[^"]*"\s*"[^"]*"', arr)
if pairs:
    print(f"\n⚠️ 缺少逗号的字符串对: {pairs[:3]}")
else:
    print("\n✅ 无缺少逗号问题")

print(f"\n_TOOL_KEYWORDS总字符数: {len(arr)}")
print("完成")
