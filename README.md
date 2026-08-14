# Relaywise

Talk to your apps instead of clicking through them. Describe what you want in
plain English and an LLM agent discovers the right connected-app tools, executes
the task, and streams its progress back to the browser.

---

## Architecture

```
Next.js (Vercel)                        AWS us-east-1
┌──────────────┐
│  App Router  │  Clerk JWT
│  Apollo      │──────────────┐
└──────────────┘              │
       ▲                      ▼
       │            ┌─────────────────────┐
       │            │      AppSync        │
       │            │  GraphQL + Lambda   │◄── relaywise-authorizer
       │            │     authorizer      │    (verifies Clerk JWT)
       │            └──────────┬──────────┘
       │                       │ askAgent
       │                       ▼
       │            ┌─────────────────────┐
       │            │    relaywise-api    │  validates, titles, enqueues
       │            └──────────┬──────────┘  returns a taskId immediately
       │                       ▼
       │              SQS FIFO ── DLQ
       │                       │
       │                       ▼
       │            ┌─────────────────────┐
       │            │relaywise-agent-worker│ LangGraph + Composio + Mantle
       │            └──────────┬──────────┘
       │                       │
       └───────────────────────┘
         progress + completion
         published to AppSync           Neon Postgres · Upstash Redis
```

### Why it is shaped this way

**Why a queue instead of answering in the request.** An agent run takes minutes;
AppSync gives a resolver 30 seconds. The API accepts the task, returns a
`taskId`, and the browser subscribes for the result. SQS FIFO keyed on the
session id keeps turns within one conversation ordered while separate
conversations run concurrently, and gives retries and a dead-letter queue for
free.

**Why AppSync rather than REST.** One authenticated surface, and subscriptions
are the natural fit for streaming agent progress. The only HTTP endpoint is the
Composio webhook, which exists because a third party posting its own JSON shape
cannot present a Clerk JWT.

**Why no VPC.** Every dependency — Neon, Upstash, Composio, Mantle — is reached
over the public internet with credentials. Putting Lambdas in a VPC would add a
NAT Gateway at roughly $32/month and buy nothing. Idle cost of this stack is
close to zero.

**Why container images.** The agent's dependency tree exceeds the 250 MB zip
limit. Images are digest-pinned, never tagged `latest`, so a rollback is exact.

---

## Repository layout

```
frontend/     Next.js App Router, Clerk auth, Apollo GraphQL client
api/          AppSync resolvers + FastAPI webhook surface (Lambda container)
backend/      LangGraph agent and SQS worker (Lambda container)
terraform/    api/ = compute and queues, orchestration/ = AppSync
scripts/      Repeatable repository tooling
```

`api/` and `backend/` are separate deployment units with separate images. They
intentionally do not share code — the API must stay small and cold-start fast,
while the worker carries the whole agent runtime.

See [api/README.md](api/README.md) and [backend/README.md](backend/README.md)
for their internal structure.

---

## Local development

Prerequisites: Node 24+, Python 3.13, `uv`, Docker Desktop, AWS CLI, Terraform.

```bash
cd frontend && npm ci && npm run dev
```

Requires `frontend/.env.local` — Clerk keys, the AppSync endpoint and API key,
and the Upstash pair. The frontend talks to the deployed AppSync API, so no
local backend is needed to exercise the chat flow.

Run the test suites:

```bash
cd api && uv sync && uv run python -m pytest -q
```

```bash
cd backend && uv sync && uv run python -m pytest -q
```

```bash
cd frontend && npm run lint && npm run typecheck && npm test -- --run
```

---

## Deploying

```powershell
./scripts/build-and-push.ps1
```

Builds all three images, pushes them, and prints digest-pinned URIs. Then apply
`terraform/api` with those digests and `deployment_phase=complete`, followed by
`terraform/orchestration` with the resulting Lambda ARNs.

Runtime configuration lives in one Secrets Manager secret,
`relaywise/lambda/secrets`. Nothing sensitive is stored in Terraform variables
or in this repository.

---

## Observability

AWS Lambda Powertools throughout. Every module logs through a child of the
service logger, so keys appended at the entrypoint (`task_id`, `session_id`,
`user_id`) appear on records emitted deep inside the agent — one filter returns
a whole request.

```bash
aws logs tail /aws/lambda/relaywise-agent-worker --follow --format short
```

Metrics: `TaskAccepted`, `TaskStarted`, `TaskCompleted`, `TaskFailed`,
`ResolverError`, `AuthAccepted`, `AuthDenied`, `AuthError`.

---

## Status

Working: authentication, conversation history, task submission, agent execution,
progress streaming.

Not yet wired: the Composio connect/sync/disconnect control plane, which lived
on the AgentCore Runtime removed during the migration to Mantle. Until it is
restored on AppSync, apps cannot be connected from the integrations page.
