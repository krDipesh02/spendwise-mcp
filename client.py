from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from config import Settings

API_KEY_HEADER = "X-API-Key"


class SpendwiseClientError(Exception):
    def __init__(self, message: str, *, kind: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.status_code = status_code


@dataclass(frozen=True)
class CategoryMatch:
    id: str
    name: str


class SpendwiseClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._telegram_api_key_cache: dict[str, str] = {}
        self._telegram_api_key_cache_lock = asyncio.Lock()

        # ✅ Shared HTTP client (connection pooling)
        self._http = httpx.AsyncClient(
            timeout=self._settings.http_timeout_seconds,
            verify=self._settings.verify_ssl,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def bootstrap_telegram_user(self, *, telegram_user_id: str, telegram_username: str | None = None, first_name: str | None = None, last_name: str | None = None) -> dict[str, Any]:
        return await self._service_request(
            "POST",
            "/auth/telegram/bootstrap",
            json={
                "telegramUserId": telegram_user_id,
                "telegramUsername": telegram_username,
                "firstName": first_name,
                "lastName": last_name,
            },
        )

    async def exchange_api_key_for_telegram(self, *, telegram_user_id: str, telegram_username: str | None = None, first_name: str | None = None, last_name: str | None = None, api_key_name: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"telegramUserId": telegram_user_id.strip()}
        if telegram_username is not None:
            body["telegramUsername"] = telegram_username
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if api_key_name:
            body["apiKeyName"] = api_key_name.strip()

        return await self._service_request("POST", "/auth/automation/api-key-exchange", json=body)

    async def get_api_key_for_telegram(self, telegram_user_id: str, *, telegram_username: str | None = None, first_name: str | None = None, last_name: str | None = None, api_key_name: str | None = None, force_refresh: bool = False) -> str:
        tid = telegram_user_id.strip()
        if not tid:
            raise SpendwiseClientError("`telegram_user_id` is required.", kind="auth")

        if not force_refresh:
            async with self._telegram_api_key_cache_lock:
                cached = self._telegram_api_key_cache.get(tid)
            if cached:
                return cached

        payload = await self.exchange_api_key_for_telegram(
            telegram_user_id=tid,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
            api_key_name=api_key_name,
        )

        raw = payload.get("apiKey")
        if not isinstance(raw, str) or not raw.strip():
            raise SpendwiseClientError("API key not returned.", kind="backend_error")

        key = raw.strip()

        async with self._telegram_api_key_cache_lock:
            self._telegram_api_key_cache[tid] = key

        return key

    def clear_telegram_api_key_cache(self, telegram_user_id: str | None = None) -> None:
        if telegram_user_id is None:
            self._telegram_api_key_cache.clear()
            return

        tid = telegram_user_id.strip()
        if tid:
            self._telegram_api_key_cache.pop(tid, None)

    async def get_profile(self, *, api_key: str) -> dict[str, Any]:
        return await self.get("/profile", api_key=api_key)

    async def list_expenses(self, *, api_key: str, from_date: str | None = None, to_date: str | None = None) -> list[dict[str, Any]]:
        params = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return await self.get("/expenses", api_key=api_key, params=params or None)

    async def get_expense(self, expense_id: str, *, api_key: str) -> dict[str, Any]:
        return await self.get(f"/expenses/{expense_id}", api_key=api_key)

    async def create_expense(self, payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
        return await self.post("/expenses", api_key=api_key, json=payload)

    async def update_expense(self, expense_id: str, payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
        return await self.put(f"/expenses/{expense_id}", api_key=api_key, json=payload)

    async def delete_expense(self, expense_id: str, *, api_key: str) -> None:
        await self.delete(f"/expenses/{expense_id}", api_key=api_key)

    async def list_categories(self, *, api_key: str) -> list[dict[str, Any]]:
        return await self.get("/categories", api_key=api_key)

    async def create_category(self, payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
        return await self.post("/categories", api_key=api_key, json=payload)

    async def update_category(self, category_id: str, payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
        return await self.put(f"/categories/{category_id}", api_key=api_key, json=payload)

    async def set_budget(self, payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
        return await self.post("/budgets", api_key=api_key, json=payload)

    async def get_budget_status(self, month: str, *, api_key: str) -> list[dict[str, Any]]:
        return await self.get("/budgets", api_key=api_key, params={"month": month})

    async def get(self, path: str, *, api_key: str, params: dict | None = None):
        return await self._request("GET", path, api_key=api_key, params=params)

    async def post(self, path: str, *, api_key: str, json: dict):
        return await self._request("POST", path, api_key=api_key, json=json)

    async def put(self, path: str, *, api_key: str, json: dict):
        return await self._request("PUT", path, api_key=api_key, json=json)

    async def delete(self, path: str, *, api_key: str):
        return await self._request("DELETE", path, api_key=api_key)

    async def _request(self, method: str, path: str, *, api_key: str, params=None, json=None):
        if not api_key.strip():
            raise SpendwiseClientError("`api_key` is required.", kind="auth")

        return await self._request_raw(
            method,
            path,
            headers={API_KEY_HEADER: api_key.strip()},
            params=params,
            json=json,
        )

    async def _service_request(self, method: str, path: str, *, params=None, json=None):
        token = self._settings.automation_service_token.strip()
        if not token:
            raise SpendwiseClientError("Service token required.", kind="auth")

        return await self._request_raw(
            method,
            path,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            json=json,
        )

    async def _request_raw(self, method, path, *, headers, params=None, json=None):
        url = f"{self._settings.backend_base_url}{path}"

        for attempt in range(3):
            try:
                response = await self._http.request(method, url, headers=headers, params=params, json=json)
                break
            except httpx.TimeoutException:
                if attempt == 2:
                    raise SpendwiseClientError("Backend timeout", kind="backend_unavailable")
                await asyncio.sleep(0.2 * (attempt + 1))

        if response.status_code == 204:
            return None

        if response.is_success:
            try:
                return response.json()
            except ValueError:
                return response.text

        raise SpendwiseClientError(response.text, kind="backend_error", status_code=response.status_code)