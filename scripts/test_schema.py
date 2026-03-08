import os
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))
tool_schemas = client.tools.get(user_id="test_user", tools=["SLACK_SEARCH_MESSAGES"])
print(tool_schemas)