import urllib.request, json
r = urllib.request.urlopen('https://autoevoai.com/api/v1/skills',timeout=10)
d = json.loads(r.read())
items = d.get('skills',[])
from collections import Counter
groups = Counter()
for x in items:
    g = x.get('group','') or x.get('type','') or 'none'
    groups[g] += 1
for g,c in groups.most_common():
    print(f'{g}: {c}')
print('---')
print(f'Total: {len(items)}')
# Show first 20 names
for x in items[:20]:
    print(f"  {x.get('name','')} = {x.get('desc','')}")
