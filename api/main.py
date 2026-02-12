import uvicorn
import asyncio
from mangum import Mangum
from app.app import app, graphql_resolver

mangum_handler = Mangum(app)

def handler(event, context):
    if "info" in event and "fieldName" in event.get("info", {}):
        return asyncio.run(graphql_resolver(event))
    else:
        return mangum_handler(event, context)

if __name__ == "__main__":
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000, reload=True)