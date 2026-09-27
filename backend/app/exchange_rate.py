import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

import httpx

from .settings import ConfigurationError, get_exchange_rate_api_key

API_BASE_URL = "https://v6.exchangerate-api.com/v6/"
REQUEST_TIMEOUT = httpx.Timeout(5.0, connect=2.0)
_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


class ExchangeRateError(RuntimeError):
    def __init__(self, public_message: str, status_code: int = 502) -> None:
        self.public_message = public_message
        self.status_code = status_code
        super().__init__(public_message)


@dataclass(frozen=True)
class Currency:
    code: str
    name: str


@dataclass(frozen=True)
class Quote:
    rate: Decimal
    timestamp: str
    rates: dict[str, Decimal]
    snapshot_date: date


_PROVIDER_ERRORS: dict[str, tuple[int, str]] = {
    "unsupported-code": (422, "The requested currency code is not supported."),
    "unknown-code": (422, "The requested currency code is not supported."),
    "invalid-key": (502, "ExchangeRate-API rejected the configured API key."),
    "inactive-account": (502, "The ExchangeRate-API account is inactive."),
    "quota-reached": (503, "The ExchangeRate-API request quota has been reached."),
    "plan-upgrade-required": (503, "The current ExchangeRate-API plan does not support this request."),
    "malformed-request": (502, "ExchangeRate-API rejected the request."),
}


class ExchangeRateClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key_provider: Callable[[], str] | None = None,
    ) -> None:
        self._http_client = http_client
        self._api_key_provider = api_key_provider or get_exchange_rate_api_key

    async def get_currencies(self) -> list[Currency]:
        payload = await self._get_json("codes")
        supported_codes = payload.get("supported_codes")
        if not isinstance(supported_codes, list):
            raise self._invalid_provider_response()

        currencies: list[Currency] = []
        for item in supported_codes:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], str)
            ):
                raise self._invalid_provider_response()
            code = item[0].strip().upper()
            name = item[1].strip()
            if not _CURRENCY_CODE.fullmatch(code) or not name:
                raise self._invalid_provider_response()
            currencies.append(Currency(code=code, name=name))

        if not currencies:
            raise self._invalid_provider_response()
        return currencies

    async def convert(self, source: str, target: str, amount: Decimal) -> Quote:
        source_code = self._normalize_currency_code(source)
        target_code = self._normalize_currency_code(target)
        if not amount.is_finite() or amount <= 0:
            raise ExchangeRateError("Amount must be a finite number greater than zero.", 422)

        rates, timestamp, snapshot_date = await self.get_latest_rates(source_code)
        rate = rates.get(target_code)
        if rate is None:
            raise ExchangeRateError("The requested currency code is not supported.", 422)
        if not rate.is_finite() or rate <= 0:
            raise self._invalid_provider_response()
        return Quote(rate=rate, timestamp=timestamp, rates=rates, snapshot_date=snapshot_date)

    async def get_latest_rates(self, base: str) -> tuple[dict[str, Decimal], str, date]:
        base_code = self._normalize_currency_code(base)
        payload = await self._get_json(f"latest/{base_code}")
        if str(payload.get("base_code", "")).upper() != base_code:
            raise self._invalid_provider_response()

        raw_rates = payload.get("conversion_rates")
        timestamp = payload.get("time_last_update_utc")
        if not isinstance(raw_rates, dict) or not isinstance(timestamp, str) or not timestamp.strip():
            raise self._invalid_provider_response()

        rates: dict[str, Decimal] = {}
        for code, raw_rate in raw_rates.items():
            if not isinstance(code, str) or not _CURRENCY_CODE.fullmatch(code.upper()):
                raise self._invalid_provider_response()
            try:
                rate = Decimal(str(raw_rate))
            except (InvalidOperation, TypeError, ValueError):
                raise self._invalid_provider_response() from None
            if not rate.is_finite() or rate <= 0:
                raise self._invalid_provider_response()
            rates[code.upper()] = rate

        raw_updated = payload.get("time_last_update_unix")
        if isinstance(raw_updated, (int, float)) and not isinstance(raw_updated, bool):
            snapshot_date = datetime.fromtimestamp(raw_updated, UTC).date()
        else:
            snapshot_date = datetime.now(UTC).date()
        if base_code not in rates:
            rates[base_code] = Decimal("1")
        return rates, timestamp, snapshot_date

    async def _get_json(self, path: str) -> dict[str, object]:
        try:
            api_key = self._api_key_provider()
        except ConfigurationError as error:
            raise ExchangeRateError(str(error), 503) from None

        try:
            response = await self._http_client.get(
                path,
                headers={"Authorization": f"Bearer {api_key}"},
            )
        except httpx.TimeoutException:
            raise ExchangeRateError("ExchangeRate-API request timed out.", 504) from None
        except httpx.RequestError:
            raise ExchangeRateError("ExchangeRate-API could not be reached.", 502) from None

        try:
            payload = response.json()
        except ValueError:
            raise self._invalid_provider_response() from None
        if not isinstance(payload, dict):
            raise self._invalid_provider_response()

        if response.is_error or payload.get("result") != "success":
            error_type = payload.get("error-type")
            status_code, message = _PROVIDER_ERRORS.get(
                error_type if isinstance(error_type, str) else "",
                (502, "ExchangeRate-API request failed."),
            )
            raise ExchangeRateError(message, status_code)
        return payload

    @staticmethod
    def _normalize_currency_code(code: str) -> str:
        normalized = code.strip().upper()
        if not _CURRENCY_CODE.fullmatch(normalized):
            raise ExchangeRateError("Currency codes must be three letters.", 422)
        return normalized

    @staticmethod
    def _invalid_provider_response() -> ExchangeRateError:
        return ExchangeRateError("ExchangeRate-API returned an invalid response.", 502)
