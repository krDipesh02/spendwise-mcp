from __future__ import annotations

from typing import Any, List, TypedDict

try:
    from fastmcp import FastMCP
except ImportError as e:
    raise ImportError("fastmcp is required to run category tools") from e

from client import SpendwiseClient


class Category(TypedDict, total=False):
    id: str
    name: str
    isActive: bool


# =========================
# Internal Helpers
# =========================

async def _resolve_api_key(
    client: SpendwiseClient,
    telegram_user_id: str,
    telegram_username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> str:
    return await client.get_api_key_for_telegram(
        telegram_user_id,
        telegram_username=telegram_username,
        first_name=first_name,
        last_name=last_name,
    )


# =========================
# Tool Registration
# =========================

def register_category_tools(mcp: FastMCP, client: SpendwiseClient) -> None:

    @mcp.tool(
        name="category_list",
        description="Lists all categories available to the authenticated user.",
    )
    async def category_list(
        telegram_user_id: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> List[Category]:
        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )
        return await client.list_categories(api_key=api_key)

    @mcp.tool(
        name="category_create",
        description="Creates a new category for the authenticated user.",
    )
    async def category_create(
        telegram_user_id: str,
        name: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Category:
        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        payload: dict[str, Any] = {"name": name}

        return await client.create_category(payload, api_key=api_key)

    @mcp.tool(
        name="category_update",
        description="Updates an existing category for the authenticated user. Note: Both name and is_active are required.",
    )
    async def category_update(
        telegram_user_id: str,
        category_id: str,
        name: str,
        is_active: bool,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Category:
        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        payload: dict[str, Any] = {
            "name": name,
            "isActive": is_active,
        }

        return await client.update_category(category_id, payload, api_key=api_key)
