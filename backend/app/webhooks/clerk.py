from fastapi import Request, HTTPException
from svix.webhooks import Webhook, WebhookVerificationError
from app.config.settings import settings
from app.config.database import AsyncSessionLocal, User

async def handle_clerk_webhook(request: Request):
    payload = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id"),
        "svix-timestamp": request.headers.get("svix-timestamp"),
        "svix-signature": request.headers.get("svix-signature"),
    }
    
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    if event["type"] == "user.created":
        data = event["data"]
        async with AsyncSessionLocal() as db:
            user = User(
                clerk_user_id=data["id"],
                email=data["email_addresses"][0]["email_address"] if data.get("email_addresses") else "",
                name=data.get("first_name") or data.get("username") or ""
            )
            db.add(user)
            await db.commit()
    
    return {"success": True}