from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from client import SpendwiseClient, SpendwiseClientError
from config import Settings


def build_client(handler):
    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    return SpendwiseClient(Settings(automation_service_token="svc-token")), MockAsyncClient


@pytest.mark.asyncio
async def test_get_profile_uses_api_key_header() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("http://localhost:8080/api/v1/profile")
        assert request.headers["X-API-Key"] == "user-key-1"
        return httpx.Response(200, json={"id": "user-1"})

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        payload = await client.get_profile(api_key="user-key-1")
    assert payload == {"id": "user-1"}


@pytest.mark.asyncio
async def test_exchange_api_key_uses_service_bearer_token() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("http://localhost:8080/api/v1/auth/automation/api-key-exchange")
        assert request.headers["Authorization"] == "Bearer svc-token"
        assert request.content  # has JSON body
        return httpx.Response(200, json={"apiKey": "spw_newkey", "id": "k1", "name": "mcp", "keyPrefix": "spw_newkey"})

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        payload = await client.exchange_api_key_for_telegram(telegram_user_id="tg-42")
    assert payload["apiKey"] == "spw_newkey"


@pytest.mark.asyncio
async def test_get_api_key_for_telegram_caches_per_telegram_id() -> None:
    exchange_calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/auth/automation/api-key-exchange"):
            exchange_calls["n"] += 1
            return httpx.Response(200, json={"apiKey": f"spw_key_{exchange_calls['n']}", "id": "k", "name": "mcp", "keyPrefix": "spw"})
        raise AssertionError(f"Unexpected URL {request.url}")

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        k1 = await client.get_api_key_for_telegram("tg-same")
        k2 = await client.get_api_key_for_telegram("tg-same")
    assert k1 == k2 == "spw_key_1"
    assert exchange_calls["n"] == 1


@pytest.mark.asyncio
async def test_get_api_key_for_telegram_force_refresh_bypasses_cache() -> None:
    exchange_calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/auth/automation/api-key-exchange"):
            exchange_calls["n"] += 1
            return httpx.Response(200, json={"apiKey": f"spw_{exchange_calls['n']}", "id": "k", "name": "mcp", "keyPrefix": "spw"})
        raise AssertionError(f"Unexpected URL {request.url}")

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        await client.get_api_key_for_telegram("tg-x")
        await client.get_api_key_for_telegram("tg-x", force_refresh=True)
    assert exchange_calls["n"] == 2


@pytest.mark.asyncio
async def test_maps_unauthorized_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Invalid API key"})

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        with pytest.raises(SpendwiseClientError) as exc:
            await client.get_profile(api_key="access-123")
    assert exc.value.kind == "auth"
    assert exc.value.status_code == 401
    assert exc.value.message == "Invalid API key"


@pytest.mark.asyncio
async def test_maps_backend_validation_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "Validation failed"})

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        with pytest.raises(SpendwiseClientError) as exc:
            await client.create_expense({"amount": -1}, api_key="access-123")
    assert exc.value.kind == "bad_request"
    assert exc.value.message == "Validation failed"


@pytest.mark.asyncio
async def test_list_expenses_after_exchange_sends_minted_api_key() -> None:
    seen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/auth/automation/api-key-exchange"):
            seen.append("exchange")
            return httpx.Response(200, json={"apiKey": "spw_minted", "id": "k", "name": "mcp", "keyPrefix": "spw_minted"})
        if "/expenses" in url and url.endswith("/expenses"):
            seen.append("expenses")
            assert request.headers["X-API-Key"] == "spw_minted"
            return httpx.Response(200, json=[])
        raise AssertionError(url)

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        api_key = await client.get_api_key_for_telegram("tg-flow")
        out = await client.list_expenses(api_key=api_key)
    assert out == []
    assert seen == ["exchange", "expenses"]


@pytest.mark.asyncio
async def test_maps_network_errors() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        with pytest.raises(SpendwiseClientError) as exc:
            await client.bootstrap_telegram_user(telegram_user_id="tg-1")
    assert exc.value.kind == "backend_unavailable"
