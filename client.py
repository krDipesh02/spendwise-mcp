from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from config import Settings

logger = logging.getLogger("spendwise_mcp.backend")


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
    """SpendWise business API client using trusted Telegram service context."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = httpx.AsyncClient(
            timeout=self._settings.http_timeout_seconds,
            verify=self._settings.verify_ssl,
        )

    async def close(self) -> None:
        logger.info("Closing backend HTTP client")
        await self._http.aclose()

    async def get_profile(self, *, telegram_user_id: str) -> dict[str, Any]:
        return await self.get("/profile", telegram_user_id=telegram_user_id)

    async def list_expenses(self, *, telegram_user_id: str, from_date: str | None = None, to_date: str | None = None) -> list[dict[str, Any]]:
        params = {key: value for key, value in (("from", from_date), ("to", to_date)) if value}
        return await self.get("/expenses", telegram_user_id=telegram_user_id, params=params or None)

    async def get_expense(self, expense_id: str, *, telegram_user_id: str) -> dict[str, Any]:
        return await self.get(f"/expenses/{expense_id}", telegram_user_id=telegram_user_id)

    async def create_expense(self, payload: dict[str, Any], *, telegram_user_id: str) -> dict[str, Any]:
        return await self.post("/expenses", telegram_user_id=telegram_user_id, json=payload)

    async def update_expense(self, expense_id: str, payload: dict[str, Any], *, telegram_user_id: str) -> dict[str, Any]:
        return await self.put(f"/expenses/{expense_id}", telegram_user_id=telegram_user_id, json=payload)

    async def delete_expense(self, expense_id: str, *, telegram_user_id: str) -> None:
        await self.delete(f"/expenses/{expense_id}", telegram_user_id=telegram_user_id)

    async def list_categories(self, *, telegram_user_id: str) -> list[dict[str, Any]]:
        return await self.get("/categories", telegram_user_id=telegram_user_id)

    async def create_category(self, payload: dict[str, Any], *, telegram_user_id: str) -> dict[str, Any]:
        return await self.post("/categories", telegram_user_id=telegram_user_id, json=payload)

    async def update_category(self, category_id: str, payload: dict[str, Any], *, telegram_user_id: str) -> dict[str, Any]:
        return await self.put(f"/categories/{category_id}", telegram_user_id=telegram_user_id, json=payload)

    async def set_budget(self, payload: dict[str, Any], *, telegram_user_id: str) -> dict[str, Any]:
        return await self.post("/budgets", telegram_user_id=telegram_user_id, json=payload)

    async def get_budget_status(self, month: str, *, telegram_user_id: str) -> list[dict[str, Any]]:
        return await self.get("/budgets", telegram_user_id=telegram_user_id, params={"month": month})

    async def get_monthly_summary(self, month: str, *, telegram_user_id: str) -> dict[str, Any]:
        return await self.get("/analytics/monthly-summary", telegram_user_id=telegram_user_id, params={"month": month})

    async def get_category_summary(self, month: str, *, telegram_user_id: str) -> list[dict[str, Any]]:
        return await self.get("/analytics/category-summary", telegram_user_id=telegram_user_id, params={"month": month})

    async def get_trend(self, from_date: str, to_date: str, *, telegram_user_id: str) -> list[dict[str, Any]]:
        return await self.get("/analytics/trend", telegram_user_id=telegram_user_id, params={"from": from_date, "to": to_date})

    async def get_outliers(self, month: str, *, telegram_user_id: str) -> list[dict[str, Any]]:
        return await self.get("/analytics/outliers", telegram_user_id=telegram_user_id, params={"month": month})

    async def get(self, path: str, *, telegram_user_id: str, params: dict | None = None):
        return await self._request("GET", path, telegram_user_id=telegram_user_id, params=params)

    async def post(self, path: str, *, telegram_user_id: str, json: dict):
        return await self._request("POST", path, telegram_user_id=telegram_user_id, json=json)

    async def put(self, path: str, *, telegram_user_id: str, json: dict):
        return await self._request("PUT", path, telegram_user_id=telegram_user_id, json=json)

    async def delete(self, path: str, *, telegram_user_id: str):
        return await self._request("DELETE", path, telegram_user_id=telegram_user_id)

    async def _request(self, method: str, path: str, *, telegram_user_id: str, params=None, json=None):
        trusted_id = telegram_user_id.strip()
        service_token = self._settings.automation_service_token.strip()
        if not trusted_id:
            raise SpendwiseClientError("Trusted Telegram identity is required.", kind="auth")
        if not service_token:
            raise SpendwiseClientError("Backend service token required.", kind="auth")
        return await self._request_raw(
            method,
            path,
            headers={
                "Authorization": f"Bearer {service_token}",
                "X-Telegram-User-Id": trusted_id,
            },
            params=params,
            json=json,
        )

    async def _request_raw(self, method: str, path: str, *, headers, params=None, json=None):
        url = f"{self._settings.backend_base_url}{path}"
        response: httpx.Response | None = None
        for attempt in range(3):
            started = time.perf_counter()
            logger.info("Backend request started: %s %s (attempt %d/3)", method, path, attempt + 1)
            try:
                response = await self._http.request(method, url, headers=headers, params=params, json=json)
                break
            except httpx.TimeoutException as exc:
                if attempt == 2:
                    logger.error("Backend request timed out: %s %s", method, path)
                    raise SpendwiseClientError("Backend timeout", kind="backend_unavailable") from exc
                logger.warning("Backend request timed out; retrying: %s %s (attempt %d/3)", method, path, attempt + 1)
            except httpx.RequestError as exc:
                if attempt == 2:
                    logger.error("Backend connection failed: %s %s (%s)", method, path, type(exc).__name__)
                    raise SpendwiseClientError("Backend connection failed", kind="backend_unavailable") from exc
                logger.warning("Backend request failed; retrying: %s %s (%s)", method, path, type(exc).__name__)
            await asyncio.sleep(0.2 * (attempt + 1))

        if response is None:
            raise SpendwiseClientError("Backend request did not produce a response.", kind="backend_unavailable")

        elapsed = time.perf_counter() - started
        if response.is_success:
            logger.info("Backend request completed: %s %s status=%d (%.3fs)", method, path, response.status_code, elapsed)
        else:
            logger.warning("Backend request returned error: %s %s status=%d (%.3fs)", method, path, response.status_code, elapsed)
        if response.status_code == 204:
            return None
        if response.is_success:
            try:
                return response.json()
            except ValueError:
                return response.text

        try:
            payload = response.json()
            message = payload.get("message") or payload.get("error") if isinstance(payload, dict) else response.text
        except ValueError:
            message = response.text
        status = response.status_code
        kind = "auth" if status in (401, 403) else "bad_request" if status == 400 else "backend_error"
        raise SpendwiseClientError(str(message), kind=kind, status_code=status)
