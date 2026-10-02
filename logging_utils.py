from __future__ import annotations

import functools
import logging
import time
import traceback
from typing import Any, Callable


def instrument_tool(mcp: Any, *, name: str, **tool_options: Any) -> Callable:
    """Register an MCP tool and log its lifecycle without logging its arguments/results."""
    register = mcp.tool(name=name, **tool_options)

    def decorate(func: Callable) -> Callable:
        logger = logging.getLogger("spendwise_mcp.tools")

        @functools.wraps(func)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            logger.info("Tool started: %s", name)
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                frames = " <- ".join(
                    f"{frame.filename}:{frame.lineno} in {frame.name}"
                    for frame in traceback.extract_tb(exc.__traceback__)
                )
                logger.error(
                    "Tool failed: %s error_type=%s kind=%s status=%s (%.3fs); trace=%s",
                    name,
                    type(exc).__name__,
                    getattr(exc, "kind", "n/a"),
                    getattr(exc, "status_code", "n/a"),
                    time.perf_counter() - started,
                    frames,
                )
                raise
            logger.info("Tool completed: %s (%.3fs)", name, time.perf_counter() - started)
            return result

        return register(wrapped)

    return decorate
