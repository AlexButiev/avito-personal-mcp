"""Runtime configuration for Avito Personal MCP."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_AVITO_ORIGIN = "https://www.avito.ru"


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration loaded from environment variables.

    No Avito credentials are accepted here. Authentication stays inside the
    user-controlled Chrome session.
    """

    cdp_url: str = DEFAULT_CDP_URL
    avito_origin: str = DEFAULT_AVITO_ORIGIN

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            cdp_url=os.getenv("AVITO_MCP_CDP_URL", DEFAULT_CDP_URL),
            avito_origin=os.getenv("AVITO_MCP_ORIGIN", DEFAULT_AVITO_ORIGIN),
        )
