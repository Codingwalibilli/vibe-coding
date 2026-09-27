from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, field_validator

from .database import Database
from .exchange_rate import (
    API_BASE_URL,
    REQUEST_TIMEOUT,
    Currency,
    ExchangeRateClient,
    ExchangeRateError,
    Quote,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = Database()
    database.initialize()
    app.state.database = database
    async with httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=REQUEST_TIMEOUT,
        follow_redirects=False,
    ) as http_client:
        app.state.exchange_rate_client = ExchangeRateClient(http_client)
        yield


app = FastAPI(title="Currency Converter API", lifespan=lifespan)


class CurrencyListResponse(BaseModel):
    currencies: list[Currency]


class ConversionResponse(BaseModel):
    source_currency: str
    target_currency: str
    amount: float
    rate: float
    converted_amount: float
    timestamp: str


class FavoritePairRequest(BaseModel):
    source_currency: str
    target_currency: str

    @field_validator("source_currency", "target_currency")
    @classmethod
    def validate_currency_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha() or not normalized.isascii():
            raise ValueError("Currency codes must be three letters.")
        return normalized


def get_exchange_rate_client(request: Request) -> ExchangeRateClient:
    return request.app.state.exchange_rate_client


def get_database(request: Request) -> Database:
    return request.app.state.database


def provider_http_error(error: ExchangeRateError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.public_message)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/currencies", response_model=CurrencyListResponse)
async def list_currencies(
    client: Annotated[ExchangeRateClient, Depends(get_exchange_rate_client)],
) -> CurrencyListResponse:
    try:
        currencies = await client.get_currencies()
    except ExchangeRateError as error:
        raise provider_http_error(error) from None
    return CurrencyListResponse(currencies=currencies)


@app.get("/api/convert", response_model=ConversionResponse)
async def convert_currency(
    source: Annotated[
        str,
        Query(alias="from", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"),
    ],
    target: Annotated[
        str,
        Query(alias="to", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"),
    ],
    amount: Annotated[
        Decimal,
        Query(gt=0, allow_inf_nan=False, max_digits=18, decimal_places=8),
    ],
    client: Annotated[ExchangeRateClient, Depends(get_exchange_rate_client)],
    database: Annotated[Database, Depends(get_database)],
) -> ConversionResponse:
    try:
        quote: Quote = await client.convert(source, target, amount)
    except ExchangeRateError as error:
        raise provider_http_error(error) from None
    converted_amount = amount * quote.rate
    database.save_daily_snapshot(
        source.upper(), quote.snapshot_date, quote.rates, quote.timestamp
    )
    database.save_conversion(
        source.upper(), target.upper(), amount, quote.rate, converted_amount, quote.timestamp
    )
    return ConversionResponse(
        source_currency=source.upper(),
        target_currency=target.upper(),
        amount=float(amount),
        rate=float(quote.rate),
        converted_amount=float(converted_amount),
        timestamp=quote.timestamp,
    )


@app.get("/api/history")
def list_conversion_history(
    database: Annotated[Database, Depends(get_database)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, list[dict[str, object]]]:
    return {"conversions": database.list_conversions(limit)}


@app.delete("/api/history")
def clear_conversion_history(
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, int]:
    return {"deleted": database.clear_conversions()}


@app.get("/api/favorites")
def list_favorites(
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, list[dict[str, object]]]:
    return {"favorites": database.list_favorites()}


@app.post("/api/favorites", status_code=201)
def add_favorite(
    pair: FavoritePairRequest,
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    favorite_id = database.add_favorite(pair.source_currency, pair.target_currency)
    if favorite_id is None:
        raise HTTPException(status_code=409, detail="This currency pair is already a favorite.")
    return {
        "id": favorite_id,
        "source_currency": pair.source_currency,
        "target_currency": pair.target_currency,
    }


@app.delete("/api/favorites/{source_currency}/{target_currency}", status_code=204)
def remove_favorite(
    source_currency: str,
    target_currency: str,
    database: Annotated[Database, Depends(get_database)],
) -> Response:
    source = FavoritePairRequest.validate_currency_code(source_currency)
    target = FavoritePairRequest.validate_currency_code(target_currency)
    if not database.remove_favorite(source, target):
        raise HTTPException(status_code=404, detail="Favorite currency pair was not found.")
    return Response(status_code=204)
