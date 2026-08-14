# Relaywise API

Two Lambda functions are built from this directory:

| Function | Dockerfile | Entrypoint |
| --- | --- | --- |
| `relaywise-api` | `Dockerfile` | `handler.lambda_handler` |
| `relaywise-authorizer` | `Dockerfile.authorizer` | `authorizer.lambda_handler` |

`authorizer.py` is packaged **alone** — its image contains no `app/` package.
It therefore must never import from `app`, or it raises `ModuleNotFoundError` at
cold start and AppSync denies every request in the system. A test enforces this.

## What the API does

Accepts an AppSync request, verifies the caller via the authorizer's resolver
context, reads or deletes conversation history, and enqueues agent tasks. It
never runs model or tool work — that belongs to the worker in `backend/`.

## Layout

```
handler.py              Lambda entrypoint; splits AppSync payloads from HTTP
main.py                 Local uvicorn server (HTTP surface only)
authorizer.py           Clerk JWT verification, self-contained by necessity
app/
  core/                 Settings and Powertools telemetry
  db/                   Models, session factory, repository
  clients/              Lazily built Redis and SQS clients
  services/             Business logic shared by both entrypoints
  routes/               FastAPI routers: health, webhooks
  graphql/              AppSync request parsing, field dispatch, resolvers
  schemas.py            Pydantic models mirroring the GraphQL types
```

### The two surfaces

**AppSync** is not HTTP — AppSync invokes the Lambda directly with a resolver
payload. `app/graphql/router.py` maps a field name to a resolver:

```python
RESOLVERS = {
    "askAgent": agent.ask_agent,
    "getUserConversations": conversation.list_conversations,
    ...
}
```

A registry rather than a chain of `if` statements: adding a field is one entry
and one function, and a field declared in the GraphQL schema with no resolver
here fails loudly instead of silently returning an error object to the browser.

**HTTP** is a normal FastAPI app built by `app/application.py`, served through
Mangum in Lambda and uvicorn locally. It is deliberately tiny: a health check
and the Composio webhook. Everything the browser calls goes through AppSync so
it inherits the Clerk authorizer.

### Identity

`AppSyncRequest.user_id` reads only the authorizer's resolver context. Client
arguments are never trusted for authorization, and every repository query is
scoped by `user_id` so a guessed session id returns nothing.

## Configuration

In Lambda, settings come from the `relaywise/lambda/secrets` JSON secret.
Locally they come from the environment. See `app/core/config.py`.

## Tests

```bash
uv sync
uv run python -m pytest -q
```
