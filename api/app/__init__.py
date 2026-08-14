"""Relaywise API.

Two entrypoints share this package:

- `handler.lambda_handler` in Lambda, routing AppSync payloads to
  `app.graphql.dispatch` and HTTP requests to the FastAPI app via Mangum
- `main.py` for local development, which serves only the HTTP surface

Layout:

    core/       settings and telemetry
    db/         models, session factory, repositories
    clients/    lazily built Redis and SQS clients
    services/   business logic shared by both entrypoints
    routes/     FastAPI routers
    graphql/    AppSync request parsing, field dispatch, resolvers
    schemas.py  Pydantic response models mirroring the GraphQL types
"""
