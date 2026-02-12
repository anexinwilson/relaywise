from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import Base, engine, get_db, User
from app.resolvers import user as user_resolver
from app.config.settings import settings
from svix.webhooks import Webhook
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    payload = await request.body()
    headers = request.headers
    
    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")
    
    if not all([svix_id, svix_timestamp, svix_signature]):
        raise HTTPException(status_code=400, detail="Missing svix headers")
    
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, {"svix-id": svix_id, "svix-timestamp": svix_timestamp, "svix-signature": svix_signature})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    if event.get("type") == "user.created":
        data = event["data"]
        async for db in get_db():
            user = User(
                clerk_user_id=data["id"],
                email=data["email_addresses"][0]["email_address"] if data.get("email_addresses") else "",
                name=data.get("first_name") or data.get("username") or ""
            )
            db.add(user)
            await db.commit()
    
    return {"success": True}


async def graphql_resolver(event: dict):
    field_name = event.get("info", {}).get("fieldName")
    user_id = event.get("request", {}).get("headers", {}).get("userId")
    
    try:
        async for db in get_db():
            if user_id:
                await user_resolver.get_or_create_user(user_id, db)
            
            if field_name == "getOrCreateUser":
                result = await user_resolver.get_or_create_user(user_id, db)
                return result
            else:
                return {"error": f"Unknown field: {field_name}", "success": False}
    
    except Exception as e:
        return {"error": str(e), "success": False}