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

    with patch("client.httpx.AsyncClient", MockAsyncClient):
        client = SpendwiseClient(Settings(backend_base_url="http://localhost:8080/api/v1", automation_service_token="svc-token"))
    return client, MockAsyncClient


@pytest.mark.asyncio
async def test_business_request_uses_service_auth_and_telegram_identity() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("http://localhost:8080/api/v1/profile")
        assert request.headers["Authorization"] == "Bearer svc-token"
        assert request.headers["X-Telegram-User-Id"] == "tg-42"
        return httpx.Response(200, json={"id": "spendwise-user-1"})

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        payload = await client.get_profile(telegram_user_id="tg-42")
    assert payload["id"] == "spendwise-user-1"


@pytest.mark.asyncio
async def test_business_request_rejects_empty_identity() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("must not make a backend request")

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        with pytest.raises(SpendwiseClientError, match="Trusted Telegram identity"):
            await client.get_profile(telegram_user_id=" ")


@pytest.mark.asyncio
async def test_maps_unauthorized_backend_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Invalid service credential"})

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        with pytest.raises(SpendwiseClientError) as exc:
            await client.get_profile(telegram_user_id="tg-42")
    assert exc.value.kind == "auth"
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_maps_backend_validation_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "Validation failed"})

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        with pytest.raises(SpendwiseClientError) as exc:
            await client.create_expense({"amount": -1}, telegram_user_id="tg-42")
    assert exc.value.kind == "bad_request"
    assert exc.value.message == "Validation failed"


@pytest.mark.asyncio
async def test_maps_network_errors() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client, mock_async_client = build_client(handler)
    with patch("client.httpx.AsyncClient", mock_async_client):
        with pytest.raises(SpendwiseClientError) as exc:
            await client.get_profile(telegram_user_id="tg-42")
    assert exc.value.kind == "backend_unavailable"
