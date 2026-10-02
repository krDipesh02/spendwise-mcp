# Spendwise MCP

## Telegram business request identity

Telegram enrollment and authorization belong to `task-automation-bot` and
`spendwise-backend`; this MCP server exposes only business tools. The bot checks
authorization directly with the backend before invoking an agent. For business
tool calls it supplies a trusted Telegram identity in the MCP request context;
the bot's MCP interceptor overwrites any model-provided `telegram_user_id`.
The MCP server then sends that identity with its backend service credential.
The backend resolves the Telegram account to the canonical SpendWise user ID
and uses that user for business operations.

Configure `MCP_AUTH_TOKEN` as a distinct secret for bot-to-MCP access, and
`SPENDWISE_AUTOMATION_SERVICE_TOKEN` for MCP-to-backend business calls. The
backend also has a bot-only `SPENDWISE_TELEGRAM_SERVICE_TOKEN` for webhook
authorization and invite activation, plus a separate administrator token.
Keep these credentials separate from one another and from the Telegram bot
token.

## Debug logging

The server writes startup and shutdown details, MCP tool start/completion/failure events, and backend request method, endpoint, status, retry, and timing information to standard output. Set `MCP_LOG_LEVEL=debug` for additional diagnostic detail. The HTTP server also logs incoming MCP requests. Tool failure logs include the exception type, backend error kind/status when available, and source locations.

Logs intentionally omit tool arguments, request/response bodies, Telegram identity fields, and API keys. Backend error logs include the HTTP status and endpoint. Do not enable HTTP wire-level logging in production because it may expose credentials or user data.
