from __future__ import annotations

from typing import TypedDict, Any

# --- FastMCP import (fail fast) ---
try:
    from fastmcp import FastMCP
except ImportError as e:
    raise ImportError("fastmcp is required to run auth tools") from e

from client import SpendwiseClient


# =========================
# Response Schemas
# =========================

class AuthResponse(TypedDict):
    authenticated: bool
    id: str | None
    email: str | None
    display_name: str | None
    base_currency: str | None
    timezone: str | None


class BootstrapResponse(TypedDict, total=False):
    id: str
    email: str
    display_name: str
    created: bool


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


# =========================
# Tool Registration
# =========================

def register_auth_tools(mcp: FastMCP, client: SpendwiseClient) -> None:

    @mcp.tool(
        name="auth_validate_telegram",
        description=(
            "Authenticate a Telegram user by generating an API key and fetching their Spendwise profile. "
            "Returns user identity and account settings."
        ),
    )
    async def auth_validate_telegram(
        telegram_user_id: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> AuthResponse:
        api_key = await _resolve_api_key(
            client,
            telegram_user_id,
            telegram_username,
            first_name,
            last_name,
        )

        profile = await client.get_profile(api_key=api_key)

        return {
            "authenticated": True,
            "id": profile.get("id"),
            "email": profile.get("email"),
            "display_name": profile.get("displayName"),
            "base_currency": profile.get("baseCurrency"),
            "timezone": profile.get("timezone"),
        }

    @mcp.tool(
        name="auth_bootstrap_telegram_user",
        description=(
            "Create or update a Telegram-linked Spendwise user for onboarding. "
            "Safe to call multiple times (idempotent)."
        ),
    )
    async def auth_bootstrap_telegram_user(
        telegram_user_id: str,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> BootstrapResponse:
        return await client.bootstrap_telegram_user(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
        )