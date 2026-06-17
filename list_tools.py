import sys
sys.path.insert(0, ".")
from api.agent_tools import list_tools
for t in list_tools():
    print(f"{t['name']:25s} - {t['category']}")
