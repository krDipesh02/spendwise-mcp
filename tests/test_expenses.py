from __future__ import annotations

import pytest

from tools.expenses import build_expense_payload, resolve_category_id


class FakeClient:
    def __init__(self, categories=None) -> None:
        self.categories = categories or []

    async def list_categories(self, *, api_key: str):
        assert api_key == "key-1"
        return self.categories


@pytest.mark.asyncio
async def test_resolve_category_id_case_insensitive() -> None:
    client = FakeClient(categories=[{"id": "cat-1", "name": "Groceries"}])
    category_id = await resolve_category_id(client, api_key="key-1", category_name=" groceries ")
    assert category_id == "cat-1"


@pytest.mark.asyncio
async def test_resolve_category_id_rejects_missing_match() -> None:
    client = FakeClient(categories=[{"id": "cat-1", "name": "Groceries"}])
    with pytest.raises(ValueError) as exc:
        await resolve_category_id(client, api_key="key-1", category_name="Travel")
    assert "No category found" in str(exc.value)


@pytest.mark.asyncio
async def test_resolve_category_id_rejects_ambiguous_match() -> None:
    client = FakeClient(
        categories=[
            {"id": "cat-1", "name": "Travel"},
            {"id": "cat-2", "name": "travel"},
        ]
    )
    with pytest.raises(ValueError) as exc:
        await resolve_category_id(client, api_key="key-1", category_name="travel")
    assert "ambiguous" in str(exc.value)


@pytest.mark.asyncio
async def test_build_expense_payload_prefers_explicit_category_id() -> None:
    client = FakeClient(categories=[{"id": "cat-1", "name": "Groceries"}])
    payload = await build_expense_payload(
        client,
        api_key="key-1",
        amount=12.5,
        currency="usd",
        spent_at="2026-03-29",
        merchant=" Store ",
        description=" Weekly shop ",
        category_name="Groceries",
        category_id="cat-explicit",
        receipt_id="receipt-1",
    )
    assert payload["categoryId"] == "cat-explicit"
    assert payload["currency"] == "USD"
    assert payload["merchant"] == "Store"
    assert payload["description"] == "Weekly shop"
    assert payload["receiptId"] == "receipt-1"


@pytest.mark.asyncio
async def test_build_expense_payload_resolves_category_name() -> None:
    client = FakeClient(categories=[{"id": "cat-1", "name": "Groceries"}])
    payload = await build_expense_payload(
        client,
        api_key="key-1",
        amount=12.5,
        currency="usd",
        spent_at="2026-03-29",
        merchant=None,
        description=None,
        category_name="Groceries",
        category_id=None,
        receipt_id=None,
    )
    assert payload["categoryId"] == "cat-1"


@pytest.mark.asyncio
async def test_build_expense_payload_rejects_invalid_date() -> None:
    client = FakeClient()
    with pytest.raises(ValueError) as exc:
        await build_expense_payload(
            client,
            api_key="key-1",
            amount=12.5,
            currency="usd",
            spent_at="03/29/2026",
            merchant=None,
            description=None,
            category_name=None,
            category_id=None,
            receipt_id=None,
        )
    assert "YYYY-MM-DD" in str(exc.value)
