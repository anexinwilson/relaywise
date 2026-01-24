from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import Base, engine, get_db
from app.resolvers import user as user_resolver

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


@app.post("/graphql-resolver")
async def graphql_resolver(event: dict):
    field_name = event.get("info", {}).get("fieldName")
    user_id = event.get("request", {}).get("headers", {}).get("userId")
    
    try:
        async for db in get_db():
            if field_name == "getOrCreateUser":
                result = await user_resolver.get_or_create_user(user_id, db)
                return result
            else:
                return {"error": f"Unknown field: {field_name}", "success": False}
    
    except Exception as e:
        return {"error": str(e), "success": False}