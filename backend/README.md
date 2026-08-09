# Relaywise backend

The backend is a modular Python application with two AWS entrypoints:

- `src/api/dispatcher.py` validates an authenticated AppSync request and queues
  one SQS FIFO task.
- `src/worker/handler.py` processes one task, runs the LangGraph workflow, and
  publishes progress/completion events.

## Source layout

```text
src/
  api/             AppSync-facing task submission adapters
  agent/           LangGraph application services and Composio integration
  credits/         Redis-backed usage accounting
  db/              SQLAlchemy models, sessions, and repositories
  memory/          Conversation metadata facade
  observability/  Powertools logs and CloudWatch metrics
  worker/          SQS Lambda handler and AppSync publisher
```

LangGraph checkpoints are stored with `AsyncPostgresSaver` in Neon. SQLAlchemy
and Alembic own only the small `conversations` metadata table. Mantle is the
single model endpoint; AgentCore Runtime/Memory and the old RAG modules are not
the application.

Run migrations from this directory with `uv run alembic upgrade head` after
`DATABASE_URL` is available. Run tests with `uv run python -m pytest -q`.
