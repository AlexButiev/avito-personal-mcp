"""Avito Personal MCP package."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("avito-personal-mcp")
except PackageNotFoundError:
    __version__ = "0+unknown"
