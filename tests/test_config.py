from __future__ import annotations

from config import get_settings


def test_mcp_auth_token_defaults_to_automation_service_token(monkeypatch) -> None:
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("SPENDWISE_AUTOMATION_SERVICE_TOKEN", "shared-token")

    settings = get_settings()

    assert settings.mcp_auth_token == "shared-token"


def test_mcp_auth_token_prefers_dedicated_override(monkeypatch) -> None:
    monkeypatch.setenv("SPENDWISE_AUTOMATION_SERVICE_TOKEN", "shared-token")
    monkeypatch.setenv("MCP_AUTH_TOKEN", "mcp-only-token")

    settings = get_settings()

    assert settings.mcp_auth_token == "mcp-only-token"
