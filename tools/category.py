from __future__ import annotations

from typing import Any, List, TypedDict

try:
    from fastmcp import FastMCP
except ImportError as e:
    raise ImportError("fastmcp is required to run category tools") from e

from client import SpendwiseClient
from logging_utils import instrument_tool


class Category(TypedDict, total=False):
    id: str
    name: str
    isActive: bool


# =========================
# Internal Helpers
# =========================

# =========================
# Tool Registration
# =========================

def register_category_tools(mcp: FastMCP, client: SpendwiseClient) -> None:

    @instrument_tool(mcp,
        name="category_list",
        description="Lists all categories available to the authenticated user.",
    )
    async def category_list(
        telegram_user_id: str,
    ) -> List[Category]:
        return await client.list_categories(telegram_user_id=telegram_user_id)

    @instrument_tool(mcp,
        name="category_create",
        description="Creates a new category for the authenticated user.",
    )
    async def category_create(
        telegram_user_id: str,
        name: str,
    ) -> Category:
        payload: dict[str, Any] = {"name": name}
        return await client.create_category(payload, telegram_user_id=telegram_user_id)

    @instrument_tool(mcp,
        name="category_update",
        description="Updates an existing category for the authenticated user. Note: Both name and is_active are required.",
    )
    async def category_update(
        telegram_user_id: str,
        category_id: str,
        name: str,
        is_active: bool,
    ) -> Category:
        payload: dict[str, Any] = {
            "name": name,
            "isActive": is_active,
        }

        return await client.update_category(category_id, payload, telegram_user_id=telegram_user_id)
