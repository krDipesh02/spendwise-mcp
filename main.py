from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from client import SpendwiseClient
from config import get_settings
from tools.analytics import register_analytics_tools
from tools.auth import register_auth_tools
from tools.budget import register_budget_tools
from tools.category import register_category_tools
from tools.expenses import register_expense_tools


def _build_mcp_auth(settings):
    token = settings.mcp_auth_token.strip()
    if not token:
        return None

    return StaticTokenVerifier(
        tokens={
            token: {
                "client_id": "spendwise-mcp-client",
                "scopes": ["mcp"],
            }
        }
    )


def create_server(settings) -> tuple[FastMCP, SpendwiseClient]:
    client = SpendwiseClient(settings)
    server = FastMCP("Spendwise MCP", auth=_build_mcp_auth(settings))

    register_auth_tools(server, client)
    register_expense_tools(server, client)
    register_analytics_tools(server, client)
    register_budget_tools(server, client)
    register_category_tools(server, client)

    return server, client


def main() -> None:
    settings = get_settings()
    server, client = create_server(settings)

    try:
        server.run(
            transport="streamable-http",
            host=settings.mcp_host,
            port=settings.mcp_port,
            path=settings.streamable_http_path,
            log_level=settings.log_level,
        )
    finally:
        import asyncio
        asyncio.run(client.close())


if __name__ == "__main__":
    main()
    