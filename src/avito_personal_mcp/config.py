"""Runtime configuration for Avito Personal MCP."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration loaded from environment variables.

    No Avito credentials are accepted here. Authentication stays inside the
    user-controlled Chrome session.
    """

    cdp_url: str = "http://127.0.0.1:9222"
    avito_origin: str = "https://www.avito.ru"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            cdp_url=os.getenv("AVITO_MCP_CDP_URL", cls.cdp_url),
            avito_origin=os.getenv("AVITO_MCP_ORIGIN", cls.avito_origin),
        )
