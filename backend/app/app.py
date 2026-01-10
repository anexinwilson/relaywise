from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.redis import redis_client
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema
from app.graphql.context import GraphQLContext

app = FastAPI()

graphql_app = GraphQLRouter(schema, context_getter=GraphQLContext)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

@app.get("/health/database")
async def health_check_database(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "success", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "failure", "database": "disconnected", "error": str(e)})


@app.get("/health/redis")
async def health_check_redis():
    try:
        redis_client.ping()
        return {"status": "success", "redis": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "failure", "redis": "disconnected", "error": str(e)}
        )