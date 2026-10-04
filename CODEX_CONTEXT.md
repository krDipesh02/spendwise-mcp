# Codex Context — MCP

Internal implementation handoff for this repository. README is deliberately limited to what this service is and its system role. This file records code structure and cross-service contract for Codex. Preserve unrelated staged work; do not commit unless asked.

## Scope and runtime

Python FastMCP Streamable HTTP server. main.py creates authenticated server, shared SpendwiseClient, registers tool modules, runs service and closes client. Defaults: 127.0.0.1:9000, /mcp, backend base http://localhost:8080/api/v1. Requires configured MCP and backend service tokens.

MCP is the agent's business capability interface. It is not a Telegram webhook, auth gateway, or invitation service. Never add invite generation, Telegram claim/approval, activation, user lookup authorization, or credential setup as MCP tools.

## Code map

- config.py: .env loading, typed Settings, defaults. Empty whitespace envs are normalized for ordinary settings; keep type parsing validated.
- main.py: StaticTokenVerifier, auth token distinctness check, tool registration and lifecycle.
- client.py: shared async httpx client, route methods, backend headers, retry policy, timeout/SSL, response and SpendwiseClientError mapping.
- logging_utils.py: instrument_tool decorator registering functions and logging lifecycle/errors/traces.
- tools/expenses.py: expense list/get/create/update/delete; date validation; optional field cleanup; category resolver.
- tools/category.py, budget.py, analytics.py: business tools and backend delegation.
- tests/: config/client/expense tool coverage and shared fixtures.

Call path: agent selects MCP tool → instrument_tool wrapper → validation and normalized payload → SpendwiseClient → backend REST. Backend receives bearer SPENDWISE_AUTOMATION_SERVICE_TOKEN and X-Telegram-User-Id; TelegramServiceAuthenticationFilter resolves to active account's canonical SpendWise user UUID. MCP bearer token authenticates bot/agent to MCP and is separate. Do not log raw arguments, Telegram identifiers unnecessarily, request bodies or credentials.

## Expense details and date correctness

expense_create tool currently declares telegram_user_id, amount, currency, spent_at as required; description claims currency INR and spent_at=today defaults, which is inconsistent with required signature. build_expense_payload validates ISO date and sends the exact input as JSON spentAt. Backend stores that date. User saw date 2023-10-05 while DB createdAt was current (Oct 2026); root cause likely agent passed wrong spent_at, not database clock.

Bot now has app/utils/date_context.py reading APP_TIMEZONE (defaults Asia/Kolkata), computing current date and injecting it as system message on every agent invocation via agent_registry.py. If user still sees old value, verify deployed bot process/image, timezone, prompt ordering/history and inspect actual MCP tool argument then backend request payload. A deterministic MCP default for omitted date may be appropriate only if desired semantics are “today when user omitted date”; do not overwrite explicit historical/future dates.

## HTTP and errors

Client retries transient connection/timeouts and selected transient responses; verify current retry list/backoff before changing. response must be checked after retries before reading status/json: historical all-retry failure caused UnboundLocalError from referencing response before assigned, later fixed with None guard and backend_unavailable exception.

SpendwiseClientError stores safe message, kind and status_code. 401 and 403 are both auth kind in client; don't map a backend 403 to HTTP 401 without an explicit interface reason. Unexpected redirects may indicate nonexistent route or wrong API base: earlier /auth/automation/api-key-exchange did not exist and request redirected to Google OAuth; inspect backend controller paths first.

Logs record backend method/path/status/time and MCP tool start/end/failure, with trace detail. Keep secrets and PII out. Request URLs include /api/v1 base; avoid double-prefixing.

## Configuration/runtime

.env.example keys: SPENDWISE_BACKEND_BASE_URL, SPENDWISE_AUTOMATION_SERVICE_TOKEN, MCP_AUTH_TOKEN, MCP_HOST, MCP_PORT, MCP_LOG_LEVEL, MCP_STREAMABLE_HTTP_PATH, SPENDWISE_HTTP_TIMEOUT_SECONDS, SPENDWISE_VERIFY_SSL. Defaults: backend localhost:8080/api/v1, host 127.0.0.1, port 9000, /mcp, timeout 15s, verify SSL true. MCP_AUTH_TOKEN and automation token required and must differ. For containers, localhost points into current container; use service DNS.

Python 3.12; .venv + requirements.txt; main.py starts server. Existing tests in tests/. Historical previous run had 15 passing, not rerun for doc work. User asked no tests unless requested.

## Existing local work

At context creation IMPLEMENTATION_SUMMARY.md, JWT_SCOPES_HLD.md and README were already staged modified/added. README was rewritten to concise purpose/role by explicit user request. Preserve those staged docs and any future changes.
