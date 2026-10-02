from __future__ import annotations

from datetime import date
from typing import TypedDict, Any, List

# --- FastMCP import (fail fast) ---
try:
    from fastmcp import FastMCP
except ImportError as e:
    raise ImportError("fastmcp is required to run expense tools") from e

from client import CategoryMatch, SpendwiseClient
from logging_utils import instrument_tool


# =========================
# Response Schemas
# =========================

class Expense(TypedDict, total=False):
    id: str
    amount: float
    currency: str
    spentAt: str
    merchant: str | None
    description: str | None
    categoryId: str | None


class DeleteResponse(TypedDict):
    status: str
    expense_id: str


# =========================
# Internal Helpers
# =========================

def _validate_iso_date(raw: str, *, field_name: str) -> None:
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"`{field_name}` must use the YYYY-MM-DD format.") from exc


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


# =========================
# Tool Registration
# =========================

def register_expense_tools(mcp: FastMCP, client: SpendwiseClient) -> None:

    @instrument_tool(mcp,
        name="expenses_list",
        description="List expenses for a Telegram-linked user. Supports optional date filters.",
    )
    async def expenses_list(
        telegram_user_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> List[Expense]:
        if from_date:
            _validate_iso_date(from_date, field_name="from_date")
        if to_date:
            _validate_iso_date(to_date, field_name="to_date")

        return await client.list_expenses(
            telegram_user_id=telegram_user_id,
            from_date=from_date,
            to_date=to_date,
        )

    @instrument_tool(mcp,
        name="expense_get",
        description="Fetch a single expense by ID.",
    )
    async def expense_get(
        telegram_user_id: str,
        expense_id: str,
    ) -> Expense:
        return await client.get_expense(expense_id, telegram_user_id=telegram_user_id)

    @instrument_tool(mcp,
        name="expense_create",
        description=(
            "Create a new expense. Amount and category_name are required. "
            "Defaults: currency=INR, spent_at=today."
        ),
    )
    async def expense_create(
        telegram_user_id: str,
        amount: float,
        currency: str,
        spent_at: str,
        merchant: str | None = None,
        description: str | None = None,
        category_name: str | None = None,
        category_id: str | None = None,
        receipt_id: str | None = None,
    ) -> Expense:
        payload = await build_expense_payload(
            client,
            telegram_user_id=telegram_user_id,
            amount=amount,
            currency=currency,
            spent_at=spent_at,
            merchant=merchant,
            description=description,
            category_name=category_name,
            category_id=category_id,
            receipt_id=receipt_id,
        )

        return await client.create_expense(payload, telegram_user_id=telegram_user_id)

    @instrument_tool(mcp,
        name="expense_update",
        description="Update an existing expense.",
    )
    async def expense_update(
        telegram_user_id: str,
        expense_id: str,
        amount: float,
        currency: str,
        spent_at: str,
        merchant: str | None = None,
        description: str | None = None,
        category_name: str | None = None,
        category_id: str | None = None,
        receipt_id: str | None = None,
    ) -> Expense:
        payload = await build_expense_payload(
            client,
            telegram_user_id=telegram_user_id,
            amount=amount,
            currency=currency,
            spent_at=spent_at,
            merchant=merchant,
            description=description,
            category_name=category_name,
            category_id=category_id,
            receipt_id=receipt_id,
        )

        return await client.update_expense(expense_id, payload, telegram_user_id=telegram_user_id)

    @instrument_tool(mcp,
        name="expense_delete",
        description="Delete an expense by ID.",
    )
    async def expense_delete(
        telegram_user_id: str,
        expense_id: str,
    ) -> DeleteResponse:
        await client.delete_expense(expense_id, telegram_user_id=telegram_user_id)

        return {"status": "deleted", "expense_id": expense_id}


# =========================
# Payload Builder
# =========================

async def build_expense_payload(
    client: SpendwiseClient,
    *,
    telegram_user_id: str,
    amount: float,
    currency: str,
    spent_at: str,
    merchant: str | None,
    description: str | None,
    category_name: str | None,
    category_id: str | None,
    receipt_id: str | None,
) -> dict[str, Any]:
    _validate_iso_date(spent_at, field_name="spent_at")

    normalized_currency = currency.strip().upper()
    if not normalized_currency:
        raise ValueError("`currency` is required.")

    if amount < 0:
        raise ValueError("`amount` must be >= 0.")

    resolved_category_id = category_id
    if not resolved_category_id and category_name:
        resolved_category_id = await resolve_category_id(
            client,
            telegram_user_id=telegram_user_id,
            category_name=category_name,
        )

    return {
        "categoryId": resolved_category_id,
        "receiptId": _clean_optional(receipt_id),
        "amount": amount,
        "currency": normalized_currency,
        "spentAt": spent_at,
        "merchant": _clean_optional(merchant),
        "description": _clean_optional(description),
    }


# =========================
# Category Resolver
# =========================

async def resolve_category_id(
    client: SpendwiseClient,
    *,
    telegram_user_id: str,
    category_name: str,
) -> str:
    normalized_name = category_name.strip().casefold()

    if not normalized_name:
        raise ValueError("`category_name` cannot be blank.")

    categories = await client.list_categories(telegram_user_id=telegram_user_id)

    matches = [
        CategoryMatch(id=c["id"], name=c["name"])
        for c in categories
        if isinstance(c.get("name"), str)
        and c["name"].strip().casefold() == normalized_name
    ]

    if not matches:
        raise ValueError(f"No category found for `{category_name}`.")

    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        raise ValueError(f"Ambiguous category `{category_name}`: {names}")

    return matches[0].id
