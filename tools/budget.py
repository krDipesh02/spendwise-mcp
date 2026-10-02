from __future__ import annotations

from typing import Any, List, TypedDict

try:
    from fastmcp import FastMCP
except ImportError as e:
    raise ImportError("fastmcp is required to run budget tools") from e

from client import SpendwiseClient
from logging_utils import instrument_tool


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

    @instrument_tool(mcp,
        name="budget_set",
        description="Creates or updates a monthly budget for the user. Category is optional (overall budget if not provided).",
    )
    async def budget_set(
        telegram_user_id: str,
        month: str,
        amount: float,
        category_id: str | None = None,
    ) -> BudgetStatus:
        _validate_month(month)

        payload: dict[str, Any] = {
            "month": month,
            "amount": amount,
        }
        if category_id is not None:
            payload["categoryId"] = category_id

        return await client.set_budget(payload, telegram_user_id=telegram_user_id)

    @instrument_tool(mcp,
        name="budget_status_get",
        description="Returns the authenticated user's budget status entries for a given month.",
    )
    async def budget_status_get(
        telegram_user_id: str,
        month: str,
    ) -> List[BudgetStatus]:
        _validate_month(month)

        return await client.get_budget_status(month, telegram_user_id=telegram_user_id)
