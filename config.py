from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())


_load_dotenv()


DEFAULT_BACKEND_BASE_URL = "http://localhost:8080/api/v1"
DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 9000
DEFAULT_HTTP_TIMEOUT_SECONDS = 15.0
DEFAULT_LOG_LEVEL = "info"
DEFAULT_STREAMABLE_HTTP_PATH = "/mcp"
DEFAULT_AUTOMATION_SERVICE_TOKEN = "changeme-service-token"
DEFAULT_MCP_AUTH_TOKEN = DEFAULT_AUTOMATION_SERVICE_TOKEN

def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    backend_base_url: str = DEFAULT_BACKEND_BASE_URL
    mcp_host: str = DEFAULT_MCP_HOST
    mcp_port: int = DEFAULT_MCP_PORT
    http_timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS
    log_level: str = DEFAULT_LOG_LEVEL
    verify_ssl: bool = True
    streamable_http_path: str = DEFAULT_STREAMABLE_HTTP_PATH
    automation_service_token: str = DEFAULT_AUTOMATION_SERVICE_TOKEN
    mcp_auth_token: str = DEFAULT_MCP_AUTH_TOKEN


def get_settings() -> Settings:
    return Settings(
        backend_base_url=os.getenv("SPENDWISE_BACKEND_BASE_URL", DEFAULT_BACKEND_BASE_URL).rstrip("/"),
        mcp_host=os.getenv("MCP_HOST", DEFAULT_MCP_HOST),
        mcp_port=int(os.getenv("MCP_PORT", str(DEFAULT_MCP_PORT))),
        http_timeout_seconds=float(
            os.getenv("SPENDWISE_HTTP_TIMEOUT_SECONDS", str(DEFAULT_HTTP_TIMEOUT_SECONDS))
        ),
        log_level=os.getenv("MCP_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        verify_ssl=_as_bool(os.getenv("SPENDWISE_VERIFY_SSL"), True),
        streamable_http_path=os.getenv("MCP_STREAMABLE_HTTP_PATH", DEFAULT_STREAMABLE_HTTP_PATH),
        automation_service_token=os.getenv("SPENDWISE_AUTOMATION_SERVICE_TOKEN", DEFAULT_AUTOMATION_SERVICE_TOKEN),
        mcp_auth_token=os.getenv(
            "MCP_AUTH_TOKEN",
            os.getenv("SPENDWISE_AUTOMATION_SERVICE_TOKEN", DEFAULT_MCP_AUTH_TOKEN),
        ),
    )
