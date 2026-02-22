import uvicorn
import asyncio
from mangum import Mangum
from app.app import app, graphql_resolver

mangum_handler = Mangum(app)

def handler(event, context):
    if "info" in event and "fieldName" in event.get("info", {}):
        # This is a GraphQL request
        return graphql_resolver(event)
    else:
        # This is an HTTP request (for webhooks, etc.)
        return mangum_handler(event, context)

if __name__ == "__main__":
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000, reload=True)