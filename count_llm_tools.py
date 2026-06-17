import re
with open("api/agent_tools.py", encoding="utf-8") as f:
    c = f.read()

all_tools = re.findall(r'@tool\("(\w+)"', c)
llm_tools = []
no_llm_tools = []

for name in all_tools:
    # Find the tool function body
    m = re.search(r'@tool\("' + name + r'".*?def _\(.*?(?=\n@tool|\n# ══|\ndef exec_tool)', c, re.DOTALL)
    if m:
        body = m.group(0)
        if "_llm(" in body:
            llm_tools.append(name)
        else:
            no_llm_tools.append(name)

print(f"Total tools: {len(all_tools)}")
print(f"Tools USING _llm(): {len(llm_tools)}")
for t in llm_tools:
    print(f"  ✅ {t}")
print(f"\nTools WITHOUT _llm(): {len(no_llm_tools)}")
for t in no_llm_tools:
    print(f"  ❌ {t}")
