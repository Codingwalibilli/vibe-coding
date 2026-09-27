import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


class ConfigurationError(RuntimeError):
    """Raised when required local configuration is unavailable."""


def get_exchange_rate_api_key() -> str:
    api_key = os.getenv("EXCHANGERATE_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "EXCHANGERATE_API_KEY is not set. Copy .env.example to .env in the "
            "project root and add your ExchangeRate-API key."
        )
    return api_key
