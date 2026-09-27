import pytest

from backend.app.settings import ConfigurationError, get_exchange_rate_api_key


def test_missing_api_key_has_setup_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXCHANGERATE_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="Copy .env.example to .env"):
        get_exchange_rate_api_key()


def test_api_key_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXCHANGERATE_API_KEY", "test-key")

    assert get_exchange_rate_api_key() == "test-key"
