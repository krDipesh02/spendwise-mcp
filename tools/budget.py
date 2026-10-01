from __future__ import annotations

from typing import Any, List, TypedDict

try:
    from fastmcp import FastMCP
except ImportError as e:
    raise ImportError("fastmcp is required to run budget tools") from e

from client import SpendwiseClient


class BudgetStatus(TypedDict):
    categoryId: str | None
    categoryName: str
    month: str
    budgetedAmount: float
    spentAmount: float
    remainingAmount: float


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


def _validate_month(month: str) -> None:
    try:
        year, month_value = map(int, month.split("-"))
        if year < 1 or not 1 <= month_value <= 12:
            raise ValueError
    except Exception:
        raise ValueError("`month` must use the YYYY-MM format.")


# =========================
# Tool Registration
# =========================

def register_budget_tools(mcp: FastMCP, client: SpendwiseClient) -> None:

    @mcp.tool(
        name="budget_set",
        description="Creates or updates a monthly budget for the user. Category is optional (overall budget if not provided).",
    )
    async def budget_set(
        telegram_user_id: str,
        month: str,
        amount: float,
        category_id: str | None = None,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> BudgetStatus:
        _validate_month(month)

        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        payload: dict[str, Any] = {
            "month": month,
            "amount": amount,
        }
        if category_id is not None:
            payload["categoryId"] = category_id

        return await client.set_budget(payload, api_key=api_key)

    @mcp.tool(
        name="budget_status_get",
        description="Returns the authenticated user's budget status entries for a given month.",
    )
    async def budget_status_get(
        telegram_user_id: str,
        month: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> List[BudgetStatus]:
        _validate_month(month)

        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        return await client.get_budget_status(month, api_key=api_key)
