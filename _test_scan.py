import sys; sys.path.insert(0, ".")
from modules.github_scanner import GithubScanner
m = GithubScanner()
r = m._fetch_repo_info("torvalds", "linux")
print(f"real API: stars={r.get('stars')}, lang={r.get('language')}")
# Also test search
r2 = m._dispatch({"action": "search", "query": "AI agent"})
print(f"search: success={r2.get('success')}, count={r2.get('total')}")
