import requests
import time
import os
import json
from dotenv import load_dotenv
import boto3
from nanoid import generate
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
BUCKET_NAME = "cognive-composio-tools"

def fetch_toolkits():
    all_toolkits = []
    cursor = None
    
    while True:
        params = {"limit": 1000, "include_deprecated": "false"}
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
    
    return [t["slug"] for t in all_toolkits]

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
            print(f"Error: {e}")
            break
    
    return all_tools

print("Fetching toolkits...")
toolkits = fetch_toolkits()
print(f"Found {len(toolkits)} toolkits")

all_tools = []
for i, toolkit in enumerate(toolkits):
    print(f"[{i+1}/{len(toolkits)}] {toolkit}...", end=" ")
    try:
        tools = fetch_tools_for_toolkit(toolkit)
        all_tools.extend(tools)
        print(f"{len(tools)} tools")
    except Exception as e:
        print(f"FAILED: {e}")
    time.sleep(0.1)

rag_tools = []
for tool in all_tools:
    if tool.get("is_deprecated", False):
        continue
    
    rag_tools.append({
        "tool_id": generate(size=12),
        "slug": tool["slug"],
        "name": tool["name"],
        "description": tool.get("description", ""),
        "toolkit": tool.get("toolkit", {}),
        "input_parameters": tool.get("input_parameters", {}),
        "no_auth": tool.get("no_auth", False),
        "version": tool.get("version", ""),
        "tags": tool.get("tags", [])
    })

print(f"\nTotal: {len(rag_tools)} tools")

def build_markdown_and_metadata(tool):
    param_schema = tool['input_parameters'].get('properties', {})
    required_params = tool['input_parameters'].get('required', [])
    toolkit_slug = tool['toolkit'].get('slug', 'unknown')
    
    md = f"# {tool['name']}\n\n## Description\n{tool['description']}\n\n## Parameters\n"
    
    if param_schema:
        for param_name, param_info in param_schema.items():
            param_type = param_info.get('type', 'string')
            param_desc = param_info.get('description', '')
            param_default = param_info.get('default')
            is_required = param_name in required_params
            
            md += f"- `{param_name}` ({param_type}, {'Required' if is_required else 'Optional'}"
            if param_default is not None:
                md += f", default: {param_default}"
            md += f") - {param_desc}\n"
    else:
        md += "No parameters required\n"
    
    optional_params = [p for p in param_schema.keys() if p not in required_params]
    
    metadata = {
        "metadataAttributes": {
            "toolkit": toolkit_slug,
            "slug": tool['slug'],
            "tool_id": tool['tool_id'],
            "no_auth": str(tool.get('no_auth', False)),
            "required_params": ",".join(required_params) if required_params else "",
            "optional_params": ",".join(optional_params) if optional_params else "",
            "tags": ",".join(tool['tags']) if tool['tags'] else "",
            "version": tool['version']
        }
    }
    
    return md, json.dumps(metadata, indent=2)

upload_lock = Lock()
uploaded_count = 0

def upload_tool(tool):
    global uploaded_count
    try:
        s3 = boto3.client('s3')
        toolkit_slug = tool['toolkit'].get('slug', 'unknown')
        base_key = f"{toolkit_slug}/{tool['slug']}"
        
        markdown, metadata_json = build_markdown_and_metadata(tool)
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{base_key}.md",
            Body=markdown.encode('utf-8'),
            ContentType='text/markdown'
        )
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{base_key}.md.metadata.json",
            Body=metadata_json.encode('utf-8'),
            ContentType='application/json'
        )
        
        with upload_lock:
            uploaded_count += 1
            if uploaded_count % 100 == 0:
                print(f"Uploaded {uploaded_count}/{len(rag_tools)} tools")
    except Exception as e:
        print(f"Failed {tool['slug']}: {e}")

with ThreadPoolExecutor(max_workers=50) as executor:
    executor.map(upload_tool, rag_tools)

print(f"\nUploaded {uploaded_count} tools to s3://{BUCKET_NAME}/")