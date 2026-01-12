from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.redis import redis_client
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema
from app.graphql.context import get_context
from fastapi.middleware.cors import CORSMiddleware
from app.webhooks.clerk import handle_clerk_webhook
from google import genai
from app.config.settings import settings


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    client = genai.Client(
        vertexai=True,
        api_key=settings.GOOGLE_VERTEX_API_KEY
    )
    app.state.genai_client = client

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")


@app.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    return await handle_clerk_webhook(request)


