import asyncio
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.exchange_rate import (
    API_BASE_URL,
    REQUEST_TIMEOUT,
    Currency,
    ExchangeRateClient,
    ExchangeRateError,
    Quote,
)
from backend.app.database import Database
from backend.app.main import app, get_database, get_exchange_rate_client
from backend.app.settings import get_exchange_rate_api_key

TEST_API_KEY = "private-test-key"


class StubExchangeRateClient:
    async def get_currencies(self) -> list[Currency]:
        return [Currency(code="EUR", name="Euro"), Currency(code="USD", name="US Dollar")]

    async def convert(self, source: str, target: str, amount: Decimal) -> Quote:
        return Quote(
            rate=Decimal("1.08"),
            timestamp="Sun, 27 Sep 2026 00:00:00 +0000",
            rates={"EUR": Decimal("1"), "USD": Decimal("1.08")},
            snapshot_date=date(2026, 9, 27),
        )


@pytest.fixture

def api_client(tmp_path: Path) -> Iterator[TestClient]:
    database = Database(tmp_path / "api-test.sqlite3")
    database.initialize()
    app.dependency_overrides[get_exchange_rate_client] = lambda: StubExchangeRateClient()
    app.dependency_overrides[get_database] = lambda: database
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_conversion_route_returns_pair_rate_amount_and_timestamp(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/convert",
        params={"from": "eur", "to": "usd", "amount": "2.5"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["source_currency"] == "EUR"
    assert result["target_currency"] == "USD"
    assert result["rate"] == pytest.approx(1.08)
    assert result["amount"] == pytest.approx(2.5)
    assert result["converted_amount"] == pytest.approx(2.7)
    assert result["timestamp"] == "Sun, 27 Sep 2026 00:00:00 +0000"
    assert TEST_API_KEY not in response.text
    history = api_client.get("/api/history").json()["conversions"]
    assert len(history) == 1
    assert history[0]["source_currency"] == "EUR"


def test_currency_list_route_returns_supported_codes(api_client: TestClient) -> None:
    response = api_client.get("/api/currencies")

    assert response.status_code == 200
    assert response.json() == {
        "currencies": [
            {"code": "EUR", "name": "Euro"},
            {"code": "USD", "name": "US Dollar"},
        ]
    }


def test_favorites_and_history_endpoints(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/favorites", json={"source_currency": "eur", "target_currency": "usd"}
    )
    duplicate = api_client.post(
        "/api/favorites", json={"source_currency": "EUR", "target_currency": "USD"}
    )

    assert created.status_code == 201
    assert duplicate.status_code == 409
    favorite = api_client.get("/api/favorites").json()["favorites"][0]
    assert favorite["source_currency"] == "EUR"
    assert favorite["target_currency"] == "USD"
    assert api_client.delete("/api/favorites/eur/usd").status_code == 204
    assert api_client.get("/api/favorites").json()["favorites"] == []
    assert api_client.get("/api/history?limit=0").status_code == 422
    assert api_client.delete("/api/history").json() == {"deleted": 0}


def test_conversion_history_survives_backend_restart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "restart.sqlite3"))
    app.dependency_overrides[get_exchange_rate_client] = lambda: StubExchangeRateClient()
    try:
        with TestClient(app) as first_run:
            response = first_run.get(
                "/api/convert",
                params={"from": "EUR", "to": "USD", "amount": "3"},
            )
            assert response.status_code == 200

        with TestClient(app) as restarted_app:
            conversions = restarted_app.get("/api/history").json()["conversions"]
            assert len(conversions) == 1
            assert conversions[0]["amount"] == "3"
            assert restarted_app.app.state.database.list_daily_snapshots(
                "EUR", date(2026, 9, 27), date(2026, 9, 27)
            )
    finally:
        app.dependency_overrides.clear()


def test_invalid_currency_format_is_rejected(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/convert",
        params={"from": "EU", "to": "USD", "amount": "1"},
    )
    invalid_amount = api_client.get(
        "/api/convert",
        params={"from": "EUR", "to": "USD", "amount": "0"},
    )

    assert response.status_code == 422
    assert invalid_amount.status_code == 422


def test_missing_api_key_returns_safe_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EXCHANGERATE_API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.get("/api/currencies")

    assert response.status_code == 503
    assert "EXCHANGERATE_API_KEY is not set" in response.json()["detail"]
    assert TEST_API_KEY not in response.text


def test_provider_uses_bearer_auth_and_maps_unsupported_code_safely() -> None:
    requests: list[httpx.Request] = []

    def success_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "result": "success",
                "base_code": "EUR",
                "conversion_rates": {"EUR": 1, "USD": 1.08},
                "time_last_update_unix": 1790467200,
                "time_last_update_utc": "Sun, 27 Sep 2026 00:00:00 +0000",
            },
        )

    async def request_quote() -> Quote:
        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=REQUEST_TIMEOUT,
            transport=httpx.MockTransport(success_handler),
        ) as http_client:
            client = ExchangeRateClient(http_client, api_key_provider=lambda: TEST_API_KEY)
            return await client.convert("eur", "usd", Decimal("2.5"))

    quote = asyncio.run(request_quote())
    assert quote.rate == Decimal("1.08")
    assert requests[0].headers["Authorization"] == f"Bearer {TEST_API_KEY}"
    assert TEST_API_KEY not in str(requests[0].url)

    def unsupported_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"result": "error", "error-type": "unsupported-code"})

    async def request_unsupported_code() -> None:
        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=REQUEST_TIMEOUT,
            transport=httpx.MockTransport(unsupported_handler),
        ) as http_client:
            client = ExchangeRateClient(http_client, api_key_provider=lambda: TEST_API_KEY)
            await client.convert("EUR", "ZZZ", Decimal("1"))

    with pytest.raises(ExchangeRateError) as error:
        asyncio.run(request_unsupported_code())
    assert error.value.status_code == 422
    assert TEST_API_KEY not in str(error.value)
    assert TEST_API_KEY not in str(requests[-1].url)


def test_provider_timeout_is_reported_without_secrets() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    async def request_currencies() -> None:
        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=REQUEST_TIMEOUT,
            transport=httpx.MockTransport(timeout_handler),
        ) as http_client:
            client = ExchangeRateClient(http_client, api_key_provider=lambda: TEST_API_KEY)
            await client.get_currencies()

    with pytest.raises(ExchangeRateError) as error:
        asyncio.run(request_currencies())

    assert error.value.status_code == 504
    assert "timed out" in str(error.value)
    assert TEST_API_KEY not in str(error.value)


def test_missing_key_is_rejected_before_network_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXCHANGERATE_API_KEY", raising=False)
    requests: list[httpx.Request] = []

    async def request_currencies() -> None:
        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=REQUEST_TIMEOUT,
            transport=httpx.MockTransport(
                lambda request: requests.append(request) or httpx.Response(200, json={})
            ),
        ) as http_client:
            client = ExchangeRateClient(http_client, api_key_provider=get_exchange_rate_api_key)
            await client.get_currencies()

    with pytest.raises(ExchangeRateError) as error:
        asyncio.run(request_currencies())

    assert error.value.status_code == 503
    assert "Copy .env.example to .env" in str(error.value)
    assert requests == []
