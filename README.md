# Currency Converter

Minimal project foundation for a React/Vite frontend and FastAPI backend. Conversion, persistence, and chart features are not implemented yet.

## ExchangeRate API plan notes

The current [Standard Requests documentation](https://www.exchangerate-api.com/docs/standard-requests) says the `/latest/{base}` endpoint is available on all plans. The [Historical Data documentation](https://www.exchangerate-api.com/docs/historical-data-requests) says historical endpoints are available only on Pro, Business, or Volume plans; unsupported accounts receive `plan-upgrade-required`. This workspace has no API key or account access, so your individual plan cannot be verified here. Historical access should be confirmed in your ExchangeRate-API dashboard before implementing that path.

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

When you have an API key, copy `.env.example` to `.env` in the project root and set `EXCHANGERATE_API_KEY` there. The key is optional for the health check, but required by ExchangeRate-dependent features. Never put the key in frontend files or commit `.env`.

## Run

Start the backend in one PowerShell terminal from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Start the frontend in a second terminal:

```powershell
Push-Location frontend
npm run dev
Pop-Location
```

The frontend is at <http://localhost:5173>. The backend health endpoint is <http://127.0.0.1:8000/health> and returns `{"status":"ok"}` with HTTP 200. Vite also proxies `/health` to the backend.

## Check

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object StatusCode, Content
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

In a Git repository, verify the secret ignore rule with:

```powershell
git check-ignore -v .env
```
