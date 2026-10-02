from __future__ import annotations

from config import get_settings
from main import _build_mcp_auth
from config import Settings


def test_mcp_auth_token_is_not_automation_service_token(monkeypatch) -> None:
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("SPENDWISE_AUTOMATION_SERVICE_TOKEN", "shared-token")

    settings = get_settings()

    assert settings.mcp_auth_token == ""


def test_mcp_auth_token_prefers_dedicated_override(monkeypatch) -> None:
    monkeypatch.setenv("SPENDWISE_AUTOMATION_SERVICE_TOKEN", "shared-token")
    monkeypatch.setenv("MCP_AUTH_TOKEN", "mcp-only-token")

    settings = get_settings()

    assert settings.mcp_auth_token == "mcp-only-token"


def test_empty_optional_values_use_defaults(monkeypatch) -> None:
    for key in (
        "MCP_HOST",
        "MCP_PORT",
        "MCP_LOG_LEVEL",
        "MCP_STREAMABLE_HTTP_PATH",
        "SPENDWISE_HTTP_TIMEOUT_SECONDS",
        "SPENDWISE_VERIFY_SSL",
    ):
        monkeypatch.setenv(key, "")

    settings = get_settings()

    assert settings.mcp_port == 9000
    assert settings.streamable_http_path == "/mcp"
    assert settings.verify_ssl is True


def test_mcp_auth_rejects_shared_backend_service_credential() -> None:
    settings = Settings(mcp_auth_token="same-secret", automation_service_token="same-secret")

    try:
        _build_mcp_auth(settings)
    except RuntimeError as exc:
        assert "distinct" in str(exc)
    else:
        raise AssertionError("expected separate MCP and backend credentials")
