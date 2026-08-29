from avito_personal_mcp.config import Settings


def test_defaults(monkeypatch):
    monkeypatch.delenv("AVITO_MCP_CDP_URL", raising=False)
    monkeypatch.delenv("AVITO_MCP_ORIGIN", raising=False)

    settings = Settings.from_env()

    assert settings.cdp_url == "http://127.0.0.1:9222"
    assert settings.avito_origin == "https://www.avito.ru"


def test_environment_override(monkeypatch):
    monkeypatch.setenv("AVITO_MCP_CDP_URL", "http://127.0.0.1:9333")
    monkeypatch.setenv("AVITO_MCP_ORIGIN", "https://example.invalid")

    settings = Settings.from_env()

    assert settings.cdp_url == "http://127.0.0.1:9333"
    assert settings.avito_origin == "https://example.invalid"
