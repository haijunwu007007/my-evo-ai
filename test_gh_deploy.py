import sys; sys.path.insert(0, ".")
import asyncio
from api.hub.github_autodeploy import search_github_async, has_docker_compose, auto_deploy_github_async

async def test():
    print("=== Search ===")
    r = await search_github_async("n8n workflow")
    print(f"Results: {len(r)}")
    for x in r[:5]:
        print(f"  {x['name']:15s} stars={x['stars']}")

    print("\n=== Detect ===")
    r = await has_docker_compose("https://github.com/n8n-io/n8n")
    print(f"Has Docker: {r['has_docker_config']}, Type: {r['deploy_type']}, Files: {r['files']}")

    print("\n=== Deploy ===")
    r = await auto_deploy_github_async("https://github.com/n8n-io/n8n")
    print(f"Success: {r.get('success')}")
    print(f"Message: {str(r.get('message',''))[:200]}")
    print(f"Project ID: {r.get('project_id','')}")

asyncio.run(test())
