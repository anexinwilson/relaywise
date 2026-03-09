import requests
import json
import os
import boto3
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

counter_lock = threading.Lock()
added_count = 0


def process_with_llm(app_name: str, raw_description: str, raw_category: str) -> tuple[str, str]:
    """Use Qwen3 to return a clean description and broad category."""
    response = bedrock.invoke_model(
        modelId="qwen.qwen3-vl-235b-a22b",
        body=json.dumps({
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional app curator. Given an app name, raw description, and raw category, output exactly two lines:\n"
                        "Line 1: A 4-5 word Title Case description of what the app does. Never include the app name. No punctuation.\n"
                        "Line 2: The single best category from this list (copy exactly): AI, Analytics, Communication, CRM, Design, Developer Tools, Ecommerce, Education, Finance, Fitness, Marketing, Productivity, Security, Social Media, Storage\n"
                        "\n"
                        "CATEGORY RULES — follow these precisely:\n"
                        "- Email clients (Gmail, Outlook, Zoho Mail, Yandex) → Communication\n"
                        "- CRM platforms (HubSpot, Salesforce, Intercom, Zendesk, Zoho, Pipedrive) → CRM\n"
                        "- Time tracking used for billing/invoicing (Harvest, Timely, Toggl) → Finance\n"
                        "- AI/ML platforms (Hugging Face, OpenAI, Replicate) → AI\n"
                        "- Design handoff or UI tools (Zeplin, Figma, Sketch) → Design\n"
                        "- Shipping and ecommerce fulfilment (Shippo, ShipStation) → Ecommerce\n"
                        "- Event ticketing platforms (Eventbrite, Ticketmaster) → Ecommerce\n"
                        "- Hospitality or field service management (Apaleo, Servicem8) → Ecommerce\n"
                        "- Nonprofit fundraising platforms (Blackbaud) → Finance\n"
                        "- Email marketing tools (Mailchimp, Kit, ConvertKit, Omnisend) → Marketing\n"
                        "- Issue trackers used by dev teams (Linear, Jira) → Developer Tools\n"
                        "- General project/task management used by all teams → Productivity\n"
                        "- Do NOT use Productivity as a default — only if the app is genuinely a general productivity tool\n"
                        "\n"
                        "Output nothing else. No thinking. No labels. No punctuation in the description.\n"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"App: {app_name}\n"
                        f"Raw description: {raw_description}\n"
                        f"Raw category: {raw_category}"
                    )
                }
            ],
            "max_tokens": 60,
            "temperature": 0.1
        })
    )
    result = json.loads(response["body"].read())
    lines = [
        l.strip().strip('"').strip("'")
        for l in result["choices"][0]["message"]["content"].strip().splitlines()
        if l.strip()
    ]
    if len(lines) < 2:
        raise ValueError(f"Expected 2 lines, got: {lines}")
    return lines[0], lines[1]


def process_toolkit(item: dict) -> dict | None:
    global added_count

    slug = item.get("slug", "")
    name = item.get("name", slug)
    meta = item.get("meta", {})
    logo = meta.get("logo", "")
    raw_description = meta.get("description", "")
    meta_categories = meta.get("categories", [])
    raw_category = meta_categories[0].get("name", "") if meta_categories else ""

    if not slug:
        return None

    try:
        description, category = process_with_llm(name, raw_description, raw_category)
    except Exception as e:
        print(f"  FAILED [{name}]: {e}")
        return None

    result = {
        "slug": slug,
        "name": name,
        "description": description,
        "category": category,
        "raw_category": raw_category,
        "logo": logo,
    }

    with counter_lock:
        added_count += 1
        print(f"  [{added_count}] {name} | {category} -> \"{description}\"")

    return result


# Fetch all toolkits
print("Fetching toolkits from Composio...")
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
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    all_toolkits.extend(data.get("items", []))
    cursor = data.get("next_cursor")
    if not cursor:
        break

all_toolkits = [t for t in all_toolkits if t.get("composio_managed_auth_schemes")]
print(f"Found {len(all_toolkits)} apps with Composio managed auth\n")
print("Processing apps...")

results = []
failed = []

with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {
        executor.submit(process_toolkit, item): item.get("slug", "")
        for item in all_toolkits
    }
    for future in as_completed(futures):
        slug = futures[future]
        try:
            result = future.result()
            if result:
                results.append(result)
            else:
                failed.append(slug)
        except Exception as e:
            print(f"  FAILED [{slug}]: {e}")
            failed.append(slug)

results.sort(key=lambda x: x["name"].lower())

with open("apps_catalog.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{len(results)} apps saved to apps_catalog.json")
if failed:
    print(f"Failed ({len(failed)}): {failed}")


















































