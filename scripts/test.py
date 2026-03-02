import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")


TEST_APPS = ["slack", "gmail", "github"]  
# TEST_APPS = None                        


print("Fetching toolkits...")
response = requests.get(
    "https://backend.composio.dev/api/v3/toolkits",
    headers={"x-api-key": COMPOSIO_API_KEY},
    params={"limit": 1000}
)
toolkits = response.json().get("items", [])

# Build managed auth lookup
managed_auth_lookup = {
    t["slug"]: t["composio_managed_auth_schemes"]
    for t in toolkits
    if t.get("composio_managed_auth_schemes")
}

if TEST_APPS:
    ALL_APPS = TEST_APPS
    print(f"TEST MODE: {len(ALL_APPS)} apps")
else:
    ALL_APPS = [t["slug"] for t in toolkits]
    print(f"FULL MODE: {len(ALL_APPS)} apps")

all_tools = []
for i, app in enumerate(ALL_APPS):
    print(f"[{i+1}/{len(ALL_APPS)}] {app}...", end=" ")
    response = requests.get(
        "https://backend.composio.dev/api/v3/tools",
        headers={"x-api-key": COMPOSIO_API_KEY},
        params={
            "toolkit_slug": app,
            "limit": 1000,
            "toolkit_versions": "latest"
        }
    )
    tools = response.json().get("items", [])
    all_tools.extend(tools)
    print(f"{len(tools)} tools")
    
    if not TEST_APPS:
        time.sleep(0.1)


rag_tools = []
for tool in all_tools:
    if tool.get("is_deprecated", False):
        continue
    
    toolkit = tool.get("toolkit", {})
    toolkit_slug = toolkit.get("slug", "unknown")

    # Filter: only managed auth or no_auth tools
    is_managed = toolkit_slug in managed_auth_lookup
    is_no_auth = tool.get("no_auth") is True
    if not is_managed and not is_no_auth:
        continue
    
    param_names = list(tool.get("input_parameters", {}).get("properties", {}).keys())
    required_params = tool.get("input_parameters", {}).get("required", [])
    
    rag_tools.append({
        "slug": tool["slug"],
        
        "name": tool["name"],
        "description": tool.get("description", ""), 
        
        "toolkit_slug": toolkit_slug,
        "toolkit_name": toolkit.get("name", ""),
        "tags": tool.get("tags", []),
        "is_no_auth": is_no_auth,
        
        "param_names": param_names,      
        "required": required_params,    
        
        "embedding_text": f"{tool['name']}: {tool.get('description', '')}. App: {toolkit.get('name', '')}"
    })


filename = "test_tools.json" if TEST_APPS else "composio_all_tools.json"
with open(filename, "w") as f:
    json.dump(rag_tools, f, indent=2)

total_size = len(json.dumps(rag_tools))
print(f"\n{len(rag_tools)} tools → {filename}")
print(f" Total: {total_size/1024:.1f}KB")