import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")

TEST_APPS = ["slack", "gmail", "twitter"]
# TEST_APPS = None

def fetch_toolkits():
    all_toolkits = []
    cursor = None
    
    while True:
        params = {"limit": 1000, "managed_by": "composio", "include_deprecated": "false"}
        if cursor:
            params["cursor"] = cursor
        
        response = requests.get(
            "https://backend.composio.dev/api/v3/toolkits",
            headers={"x-api-key": COMPOSIO_API_KEY},
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        all_toolkits.extend(data.get("items", []))
        
        cursor = data.get("next_cursor")
        if not cursor:
            break
    
    return [t for t in all_toolkits if t.get("composio_managed_auth_schemes")]

def fetch_tools_for_toolkit(toolkit_slug):
    all_tools = []
    cursor = None
    
    while True:
        params = {
            "toolkit_slug": toolkit_slug,
            "limit": 1000,
            "toolkit_versions": "latest",
            "include_deprecated": "false"
        }
        if cursor:
            params["cursor"] = cursor
        
        try:
            response = requests.get(
                "https://backend.composio.dev/api/v3/tools",
                headers={"x-api-key": COMPOSIO_API_KEY},
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            all_tools.extend(data.get("items", []))
            
            cursor = data.get("next_cursor")
            if not cursor:
                break
        except Exception as e:
            print(f"Error fetching {toolkit_slug}: {e}")
            break
    
    return all_tools

print("Fetching toolkits...")
toolkits = fetch_toolkits()
print(f"Found {len(toolkits)} truly managed toolkits")

managed_auth_lookup = {t["slug"]: t["composio_managed_auth_schemes"] for t in toolkits}

if TEST_APPS:
    ALL_APPS = [t for t in toolkits if t["slug"] in TEST_APPS]
    print(f"TEST MODE: {len(ALL_APPS)} apps")
else:
    ALL_APPS = toolkits
    print(f"FULL MODE: {len(ALL_APPS)} apps")

all_tools = []
for i, toolkit in enumerate(ALL_APPS):
    slug = toolkit["slug"]
    print(f"[{i+1}/{len(ALL_APPS)}] {slug}...", end=" ")
    try:
        tools = fetch_tools_for_toolkit(slug)
        all_tools.extend(tools)
        print(f"{len(tools)} tools")
    except Exception as e:
        print(f"FAILED: {e}")
    time.sleep(0.1)

rag_tools = []
for tool in all_tools:
    if tool.get("is_deprecated", False):
        continue

    toolkit = tool.get("toolkit", {})
    toolkit_slug = toolkit.get("slug", "unknown")

    rag_tools.append({
        "slug": tool["slug"],
        "name": tool["name"],
        "description": tool.get("description", ""),
        "toolkit": toolkit,
        "tags": tool.get("tags", []),
        "no_auth": tool.get("no_auth", False),
        "version": tool.get("version", ""),
        "scopes": tool.get("scopes", []),
        "input_parameters": tool.get("input_parameters", {}),
        "managed_auth_schemes": managed_auth_lookup.get(toolkit_slug, []),
        "embedding_text": f"{tool['name']}: {tool.get('description', '')}. App: {toolkit.get('name', '')}"
    })

filename = "test_tools.json" if TEST_APPS else "composio_all_tools.json"
with open(filename, "w") as f:
    json.dump(rag_tools, f, indent=2)

total_size = len(json.dumps(rag_tools))
print(f"\n{len(rag_tools)} tools → {filename}")
print(f"Total: {total_size/1024:.1f}KB")