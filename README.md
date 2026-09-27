# Currency Converter

A React/Vite and FastAPI currency converter with SQLite history and favorites, rate-trend charts, and a five-currency travel-budget comparison. Run it in keyless demo mode for a showcase, or configure an ExchangeRate-API key for live rates.

## What Was Built

1. **Project foundation:** `frontend/` contains the Vite/React app; `backend/` contains the FastAPI app and tests. `.env.example` is a blank template, and `.gitignore` excludes `.env` and local SQLite files.
2. **Rate API:** `backend/app/exchange_rate.py` calls ExchangeRate-API from the server, uses a request timeout, sends the key as a Bearer header, validates provider responses, and maps provider failures to safe messages. The frontend never receives the key.
3. **SQLite persistence:** `backend/app/database.py` creates the conversion-history, favorites, and daily-rate-snapshot tables. Successful conversions are saved; daily live rates are saved by base currency and provider date. Demo rates are recorded as demo history but are not stored as live snapshots.
4. **FastAPI routes:** `backend/app/main.py` provides:
   - `GET /health` for a basic health check.
   - `GET /api/currencies` for supported currencies.
   - `GET /api/convert?from=EUR&to=USD&amount=1` for one conversion.
   - `GET /api/convert/budget?from=EUR&amount=100` for USD, EUR, GBP, JPY, and AUD comparisons.
   - `GET /api/rates/history?from=EUR&to=USD&days=30` for 7-, 30-, or 90-day history.
   - `GET` and `DELETE /api/history` to list or clear recent conversions.
   - `GET`, `POST`, and `DELETE /api/favorites` routes to list, add, and remove favorite pairs. Duplicate favorites return HTTP 409.
5. **Converter screen:** `frontend/src/App.jsx` loads currencies and saved data, provides amount and currency controls, swaps pairs, and displays quote/error states. The backend performs rate fetching and conversion calculations.
6. **Trend chart:** `frontend/src/RateChart.jsx` renders the rate series with date/rate axes and hover values. The 7D, 30D, and 90D buttons select the requested range. Actual history is based on saved live daily snapshots; missing dates are not invented. Demo mode labels its illustrative trend clearly.
7. **Favorites and recent activity:** The converter screen lets you save/remove favorite pairs, select a saved pair, revisit recent conversions, and clear recent history.
8. **Travel Budget mode:** Turn on the toggle to enter one amount and compare all five target currencies in a table. Turning it off returns to the normal pair converter.

## Requirements

- Node.js 22.12 or newer and npm
- Python 3.10 or newer

## Step 1: Install Dependencies

Run from the project root in PowerShell:

```powershell
Push-Location frontend
npm install
Pop-Location

py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## Step 2: Choose Demo or Live Rates

### Keyless demo

Demo mode needs no API key. It uses a small sample currency set and illustrative rates/chart movement; the UI labels these as sample data. From the project root, set demo mode in the backend terminal before starting FastAPI:

```powershell
$env:CURRENCY_DEMO_MODE = 'true'
```

### Live ExchangeRate-API rates

Get a key from the [ExchangeRate-API sign-up page](https://app.exchangerate-api.com/sign-up). Copy `.env.example` to `.env` in the project root, then add the key to the `EXCHANGERATE_API_KEY` setting in `.env`. Do not paste the key into frontend code or commit `.env`. Leave `CURRENCY_DEMO_MODE` unset to use the live provider.

The provider's [latest-rate endpoint](https://www.exchangerate-api.com/docs/standard-requests) is listed as available on all plans. Provider historical endpoints are limited to paid plans; this project uses locally stored daily snapshots for live chart history instead.

## Step 3: Start the Backend

In the first PowerShell terminal, from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

The backend is at <http://127.0.0.1:8000>. Check health at <http://127.0.0.1:8000/health>.

## Step 4: Start the Frontend

In a second PowerShell terminal, from the project root:

```powershell
Push-Location frontend
npm run dev
Pop-Location
```

Open <http://localhost:5173>. Vite forwards `/health` and `/api` requests to FastAPI.

## Step 5: Run Tests and Build

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
Push-Location frontend
npm run build
Pop-Location
```

The SQLite database is created automatically at `backend/data/currency.sqlite3` on backend startup. It is local and ignored by Git.

## Historical Data Notes

Live chart history accumulates from daily rate snapshots as the app fetches rates; the chart will not have a full 30 days of real observations on first run. Without saved live observations, the chart shows an empty-history state. Demo mode generates illustrative chart points for preview only, not historical market data.