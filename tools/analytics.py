from __future__ import annotations

from datetime import date
from typing import Any, TypedDict, List

# --- FastMCP import (fail fast instead of silent fallback) ---
try:
    from fastmcp import FastMCP
except ImportError as e:
    raise ImportError("fastmcp is required to run analytics tools") from e

from client import SpendwiseClient

class CategorySummary(TypedDict):
    category: str
    total: float


class DailyTrend(TypedDict):
    date: str
    total: float


class MonthlySummary(TypedDict):
    total: float
    categories: List[CategorySummary]


# =========================
# Internal Helpers
# =========================

async def _user_api_key(
    client: SpendwiseClient,
    telegram_user_id: str,
    *,
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


async def _resolve_api_key(
    client: SpendwiseClient,
    telegram_user_id: str,
    telegram_username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> str:
    return await _user_api_key(
        client,
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


def _validate_iso_date(raw: str, *, field_name: str) -> None:
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"`{field_name}` must use the YYYY-MM-DD format.") from exc


# =========================
# Tool Registration
# =========================

def register_analytics_tools(mcp: FastMCP, client: SpendwiseClient) -> None:

    @mcp.tool(
        name="analytics_monthly_summary",
        description=(
            "Return a monthly spending summary for the specified month (YYYY-MM format). "
            "Includes total spend and category breakdown."
        ),
    )
    async def analytics_monthly_summary(
        telegram_user_id: str,
        month: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> MonthlySummary:
        _validate_month(month)

        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        return await client.get_monthly_summary(month, api_key=api_key)

    @mcp.tool(
        name="analytics_category_summary",
        description=(
            "Return per-category spending totals for a given month (YYYY-MM format)."
        ),
    )
    async def analytics_category_summary(
        telegram_user_id: str,
        month: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> List[CategorySummary]:
        _validate_month(month)

        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        return await client.get_category_summary(month, api_key=api_key)

    @mcp.tool(
        name="analytics_trend",
        description=(
            "Return daily spending totals for a given inclusive date range (YYYY-MM-DD)."
        ),
    )
    async def analytics_trend(
        telegram_user_id: str,
        from_date: str,
        to_date: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> List[DailyTrend]:
        _validate_iso_date(from_date, field_name="from_date")
        _validate_iso_date(to_date, field_name="to_date")

        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        return await client.get_trend(from_date, to_date, api_key=api_key)

    @mcp.tool(
        name="analytics_outliers",
        description=(
            "Return unusual or anomalous spending entries for a given month (YYYY-MM format)."
        ),
    )
    async def analytics_outliers(
        telegram_user_id: str,
        month: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> List[dict]:
        _validate_month(month)

        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        return await client.get_outliers(month, api_key=api_key)