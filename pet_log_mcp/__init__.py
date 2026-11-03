"""Local MCP server for household pet care notes (education/organizing only)."""

from .server import serve, handle_request
from .store import JsonStore
from .tools import TOOLS, ToolError

from .server import __version__  # noqa: E402

__all__ = [
    "serve",
    "handle_request",
    "JsonStore",
    "ToolError",
    "TOOLS",
    "__version__",
]
