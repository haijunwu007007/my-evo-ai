"""修复agent_tools.py中f-string语法错误"""

with open("api/agent_tools.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

# Fix pattern: f"xxx执行失败: {e}"}"}  ->  f"xxx执行失败: {e}"}
# The issue is the round 4/5 generated blocks have double closing
# Pattern: f"word执行失败: {e}\"}\"}  should be f"word执行失败: {e}\"}

# Find all lines with 执行失败
lines = content.split("\n")
fixed_count = 0
new_lines = []

for i, line in enumerate(lines):
    if "执行失败" in line and "return" in line:
        # Fix: replace \"}\"} at end with \"}
        # The correct pattern should end with: f"xxx执行失败: {e}"}
        # But some have: f"xxx执行失败: {e}\"}"}
        old_line = line
        # Fix double closing: "}"}  -> "}
        line = re.sub(r'\\"\\}\\\"\}', '\\"}\\', line)
        # Also fix: {e}\"}\"} -> {e}\"}
        line = line.replace('{e}\\"\\"\\"}', '{e}\\"\\"}')
        line = line.replace('{e}\\"}\\\\"}', '{e}\\"\\"}')
        # Simpler approach: if line doesn't end cleanly, fix it
        if line != old_line:
            fixed_count += 1
            print(f"Fixed line {i+1}")

    new_lines.append(line)

content = "\n".join(new_lines)

# More robust: just rewrite all the error lines properly
# Replace all instances of the bad pattern
content = re.sub(
    r'f"(\w+)执行失败: \{e\}\\\"\\}\\\"',
    r'f"\1执行失败: {e}\\"}',
    content
)

# Also try: some have }\"}\"} at the end
content = content.replace('}\\"\\"\\"}', '}\\"\\"}')

with open("api/agent_tools.py", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Fixed {fixed_count} lines. Verifying...")

import py_compile
try:
    py_compile.compile("api/agent_tools.py", doraise=True)
    print("✅ agent_tools.py 语法通过")
except py_compile.PyCompileError as e:
    print(f"❌ Still has errors: {e}")
