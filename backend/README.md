# Relaywise agent worker

Builds `relaywise-agent-worker` from `Dockerfile.worker`, entrypoint
`worker.handler.handler`.

Consumes one task from the SQS FIFO queue, runs the LangGraph agent against
Composio's connected-app tools and the Mantle model, and publishes progress and
completion back through AppSync.

## Layout

```
src/
  worker/         SQS entrypoint and AppSync completion publisher
  agent/          LangGraph execution, Composio discovery, prompts, intent routing
  memory/         Conversation metadata facade
  db/             SQLAlchemy models, session, repository
  credits/        Token accounting (written and tested, not yet wired)
  observability/  Powertools logger and metrics
  config.py       Settings, from Secrets Manager in Lambda
  utils.py        Module loggers, parented to the Powertools logger
alembic/          Neon schema migrations
```

## How a task flows

1. `worker/handler.py` receives one SQS record and appends `task_id`,
   `session_id`, and `user_id` to the logger. Every record emitted below this
   point carries them.
2. `agent/intent.py` routes unambiguous conversational messages — greetings,
   "who are you" — without an LLM call.
3. Otherwise `agent/service.py` opens a Composio session, discovers only the
   tools the request needs, and runs the LangGraph agent.
4. Graph state is checkpointed to Neon with `AsyncPostgresSaver`, keyed on the
   conversation id, so a follow-up message resumes the same thread.
5. `worker/publisher.py` publishes completion to AppSync; the browser is
   subscribed on the task id.

## Persistence

| Store | Owns |
| --- | --- |
| Neon, app tables | Conversation titles and message history |
| Neon, LangGraph tables | Graph checkpoints, managed by `AsyncPostgresSaver` |
| Upstash Redis | Connected-app cache, credit balances |

Alembic manages only the small application tables. The checkpointer creates and
owns its own schema.

## Failure handling

`worker/handler.py` distinguishes two cases:

- **Agent-level** — the model declined or a tool refused. Reported as `FAILED`
  with a user-facing message; not retried, because retrying a refusal only
  burns tokens.
- **Infrastructure** — Neon, Mantle, Composio, or the publisher is unreachable.
  Re-raised so SQS retries and, after `maxReceiveCount`, routes to the DLQ.

Note: `AgentService.execute_task` currently catches broadly, so most
infrastructure faults are converted to the agent-level path before the worker
can see them. Tracked in `scratch/audits` as item D2.

## Commands

```bash
uv sync
uv run python -m pytest -q
uv run alembic upgrade head    # only when the Neon schema needs migrating
```
