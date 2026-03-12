import requests
import os
import json
from dotenv import load_dotenv
import boto3
from nanoid import generate
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import ftfy

load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
BUCKET_NAME = "cognive-composio-toolkits"

s3_client = boto3.client("s3")


def clean_text(text: str) -> str:
    if not text:
        return ""
    return ftfy.fix_text(text)


def fetch_toolkits():
    toolkits = []
    cursor = None
    while True:
        params = {"limit": 1000, "include_deprecated": "false"}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(
            "https://backend.composio.dev/api/v3/toolkits",
            headers={"x-api-key": COMPOSIO_API_KEY},
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        toolkits.extend(data.get("items", []))
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return toolkits


def fetch_tools_for_toolkit(toolkit_slug):
    tools = []
    cursor = None
    while True:
        params = {
            "toolkit_slug": toolkit_slug,
            "limit": 1000,
            "toolkit_versions": "latest",
            "include_deprecated": "false",
        }
        if cursor:
            params["cursor"] = cursor
        try:
            response = requests.get(
                "https://backend.composio.dev/api/v3/tools",
                headers={"x-api-key": COMPOSIO_API_KEY},
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            tools.extend(data.get("items", []))
            cursor = data.get("next_cursor")
            if not cursor:
                break
        except Exception as e:
            print(f"Error fetching tools for {toolkit_slug}: {e}")
            break
    return tools


print("Fetching toolkits...")
toolkits_data = fetch_toolkits()
print(f"Found {len(toolkits_data)} toolkits")

managed_auth_lookup = {
    t["slug"]: t["composio_managed_auth_schemes"]
    for t in toolkits_data
    if t.get("composio_managed_auth_schemes")
}

description_cache = {
    t["slug"]: clean_text(t.get("meta", {}).get("description", ""))
    for t in toolkits_data
}

toolkit_name_cache = {
    t["slug"]: t.get("name", t["slug"])
    for t in toolkits_data
}

toolkit_slugs = [t["slug"] for t in toolkits_data]

all_tools = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {
        executor.submit(fetch_tools_for_toolkit, slug): slug
        for slug in toolkit_slugs
    }
    for i, future in enumerate(as_completed(futures), 1):
        slug = futures[future]
        try:
            tools = future.result()
            all_tools.extend(tools)
            print(f"[{i}/{len(toolkit_slugs)}] {slug}: {len(tools)} tools")
        except Exception as e:
            print(f"FAILED {slug}: {e}")

rag_tools = []
for tool in all_tools:
    if tool.get("is_deprecated", False):
        continue

    toolkit = tool.get("toolkit", {})
    toolkit_slug = toolkit.get("slug", "unknown")

    is_no_auth = tool.get("no_auth") is True
    is_managed = toolkit_slug in managed_auth_lookup
    if not is_managed and not is_no_auth:
        continue

    rag_tools.append({
        "tool_id": generate(size=12),
        "slug": tool["slug"],
        "toolkit_name": toolkit_name_cache.get(toolkit_slug, toolkit_slug),
        "name": tool["name"],
        "slug_description": clean_text(tool.get("description", "")),
        "human_description": clean_text(tool.get("human_description", "")),
        "app_description": description_cache.get(toolkit_slug, ""),
        "required": tool.get("input_parameters", {}).get("required", []),
        "toolkit": toolkit,
        "version": tool.get("version", "")
    })

print(f"\nTotal: {len(rag_tools)} tools")


def build_markdown_and_metadata(tool):
    toolkit_slug = tool["toolkit"].get("slug", "unknown")
    toolkit_name = tool["toolkit_name"]

    required_str = ", ".join(tool["required"]) if tool["required"] else "none"

    md = f"# {toolkit_name} - {tool['name']}\n"
    md += f"Toolkit: {toolkit_slug}\n"
    md += f"Slug: {tool['slug']}\n"
    md += f"Tool: {tool['name']} on {toolkit_name}\n\n"
    md += f"slug_description: {tool['slug_description'].strip()}\n"
    if tool["human_description"]:
        md += f"human_description: {tool['human_description'].strip()}\n"
    if tool["app_description"]:
        md += f"app_description: {tool['app_description'].strip()}\n"
    md += f"required: {required_str}\n"

    metadata = {
        "metadataAttributes": {
            "toolkit": toolkit_slug,
            "slug": tool["slug"],
            "version": tool["version"]
        }
    }

    return md, json.dumps(metadata, indent=2)


upload_lock = Lock()
uploaded_count = 0


def upload_tool(tool):
    global uploaded_count
    try:
        toolkit_slug = tool["toolkit"].get("slug", "unknown")
        base_key = f"{toolkit_slug}/{tool['slug']}"
        markdown, metadata_json = build_markdown_and_metadata(tool)

        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{base_key}.md",
            Body=markdown.encode("utf-8"),
            ContentType="text/markdown"
        )
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{base_key}.md.metadata.json",
            Body=metadata_json.encode("utf-8"),
            ContentType="application/json"
        )

        with upload_lock:
            uploaded_count += 1
            if uploaded_count % 100 == 0:
                print(f"Uploaded {uploaded_count}/{len(rag_tools)} tools")

    except Exception as e:
        print(f"Failed {tool['slug']}: {e}")


print("\nUploading to S3...")
with ThreadPoolExecutor(max_workers=25) as executor:
    executor.map(upload_tool, rag_tools)

print(f"\nUploaded {uploaded_count} tools to s3://{BUCKET_NAME}/")