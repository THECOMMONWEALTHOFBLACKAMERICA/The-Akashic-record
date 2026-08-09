# T.A.R. Bounded Autonomous Runtime

T.A.R. autonomy is a planner/executor layered above the existing source, memory, document and media primitives. It is intentionally bounded rather than an unrestricted self-directed process.

## Invariants

- A run has a hard step budget (`TAR_AUTONOMY_MAX_STEPS`, maximum 10).
- Only built-in allowlisted tools may be planned.
- Autonomous code/shell execution is not available.
- Credential changes, purchases, messaging, destructive operations and governance mutation are not autonomous tools.
- Every run and every step carries the caller's workspace ID.
- Plans, outputs, failures and timestamps are persisted.
- The API performs the run in the current request; T.A.R. does not claim hidden background work.
- Durable worker execution is available by submitting task kind `agent`; the same tool and step boundaries apply.

## Default tools

`search,recall,research,pdf,docx,image,video`

Image/video steps require configured provider adapters. Unconfigured providers fail explicitly rather than producing fake outputs.

## Planning

When a planning-capable LLM is configured, T.A.R. requests a minimal JSON plan constrained to the allowlist and budget. The returned plan is validated; unknown tools are discarded. If the provider fails or returns unusable output, T.A.R. uses a deterministic fallback plan.

## Persistence

- `agent_runs` stores goal, validated plan, status and final result.
- `agent_steps` stores each tool invocation and its result/error.
- API completion/failure is also recorded in the workspace audit chain.

## API

`POST /v1/agents/run`

```json
{"goal":"Research the history of a named community and create a PDF report"}
```

`GET /v1/agents/runs/{run_id}` returns the workspace-owned run and step history.

## Security note

Autonomy does not expand the privileges of the caller or node. It orchestrates already-authorized primitives. Higher-risk execution (for example explicit Python execution through the separate task primitive) remains independently gated and is deliberately absent from autonomous planning.
