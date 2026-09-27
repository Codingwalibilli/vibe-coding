# Currency Converter

A small React/Vite and FastAPI currency converter with SQLite history/favorites, rate trends, and travel-budget comparison.

## ExchangeRate API plan notes

The [Standard Requests documentation](https://www.exchangerate-api.com/docs/standard-requests) says latest rates are available on all plans. The [Historical Data documentation](https://www.exchangerate-api.com/docs/historical-data-requests) limits provider history to Pro, Business, or Volume plans. This app builds live history from daily rate snapshots saved in SQLite. Its optional local demo mode uses clearly labeled illustrative rates and chart movement; it does not save those as live snapshots.

## Prerequisites

- Node.js 22.12 or newer and npm
- Python 3.10 or newer

## Install

Run these commands from the project root in PowerShell:

```powershell
Push-Location frontend
npm install
Pop-Location
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

No API key is needed for the local demo. For live ExchangeRate-API rates, get a key from the [ExchangeRate-API account page](https://app.exchangerate-api.com/sign-up), copy `.env.example` to `.env` in the project root, and set `EXCHANGERATE_API_KEY` there. The key stays on the backend; never put it in frontend files or commit `.env`.

## Run

Start the backend in one PowerShell terminal from the project root in demo mode:

```powershell
$env:CURRENCY_DEMO_MODE = 'true'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

For live rates, set the key in `.env` and omit `CURRENCY_DEMO_MODE`.

Start the frontend in a second terminal:

```powershell
Push-Location frontend
npm run dev
Pop-Location
```

The frontend is at <http://localhost:5173>. The backend health endpoint is <http://127.0.0.1:8000/health>. Vite proxies both `/health` and `/api` to FastAPI.

## Included workflows

- Convert between supported currencies with a clear quote timestamp.
- View 7-, 30-, or 90-day rates from locally stored daily live snapshots; missing dates are not interpolated.
- Save favorite currency pairs and revisit recent conversions.
- Toggle Travel Budget to compare one base amount in USD, EUR, GBP, JPY, and AUD.
- Use the labeled demo mode without configuring a key. Demo chart data is illustrative, not historical market data.

## Check

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object StatusCode, Content
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

In a Git repository, verify the secret ignore rule with:

```powershell
git check-ignore -v .env
```
