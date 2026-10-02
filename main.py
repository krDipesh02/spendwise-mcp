from __future__ import annotations

import logging

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from client import SpendwiseClient
from config import get_settings
from tools.analytics import register_analytics_tools
from tools.budget import register_budget_tools
from tools.category import register_category_tools
from tools.expenses import register_expense_tools

logger = logging.getLogger("spendwise_mcp")


def _build_mcp_auth(settings):
    token = settings.mcp_auth_token.strip()
    if not token:
        raise RuntimeError("MCP_AUTH_TOKEN must be configured")
    if token == settings.automation_service_token.strip():
        raise RuntimeError("MCP_AUTH_TOKEN must be distinct from SPENDWISE_AUTOMATION_SERVICE_TOKEN")

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

    register_expense_tools(server, client)
    register_analytics_tools(server, client)
    register_budget_tools(server, client)
    register_category_tools(server, client)

    logger.info("Registered Spendwise MCP tools")

    return server, client


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info(
        "Starting Spendwise MCP server: host=%s port=%d path=%s backend=%s timeout=%.1fs verify_ssl=%s",
        settings.mcp_host,
        settings.mcp_port,
        settings.streamable_http_path,
        settings.backend_base_url,
        settings.http_timeout_seconds,
        settings.verify_ssl,
    )
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
        logger.info("Stopping Spendwise MCP server")
        asyncio.run(client.close())


if __name__ == "__main__":
    main()
