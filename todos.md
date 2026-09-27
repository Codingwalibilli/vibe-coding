# Currency Converter Build Plan

- [x] Initialize Git and push the initial project commit (`7de7c67`). Keep future checkpoint commits short and section-specific.

## 1. Project foundation and secret handling
- [x] Set up a Vite React frontend and a FastAPI backend in a clear `frontend/` and `backend/` structure.
- [x] Keep the frontend/backend folder split simple and readable; avoid extra layering without a clear need.
- [x] Add `.env` to `.gitignore` as the first repository change; provide `.env.example` containing only `EXCHANGERATE_API_KEY=` and no real key.
- [x] Add backend configuration that reads `EXCHANGERATE_API_KEY` from the environment and fails safely with a clear setup message when it is absent.
- [x] Check current ExchangeRate API documentation and document plan limits: latest rates are available on all plans; historical data requires Pro, Business, or Volume. Individual account access could not be verified because no key was provided.
- [x] Add install/run instructions and basic health checks.

**Checkpoint 1 - PASSED:** Verified the `.env` ignore rule with the non-Git workspace fallback (this folder has no `.git` repository), confirmed `.env.example` contains only `EXCHANGERATE_API_KEY=`, installed frontend and backend dependencies, built the frontend, passed both settings tests, started both services, and confirmed the backend health route and Vite proxy return HTTP 200.
- [ ] After Checkpoint 1 passes, make a short commit: `Section 1: foundation and secret handling done`.

## 2. Exchange-rate service and conversion API
- [x] Implement a backend ExchangeRate API client with timeouts, input validation, and useful handling for missing keys, unsupported currencies, provider errors, and rate limits.
- [x] Add a currency-list endpoint and a conversion endpoint that accepts source currency, target currency, and amount, returning the rate, converted amount, and timestamp.
- [x] Keep provider credentials on the server; never expose the key to the frontend or include it in logs/responses.
- [x] Keep rate fetching, conversion math, and validation in FastAPI; the frontend only handles input and displays returned data.

**Checkpoint 2 - PASSED (keyless demo/mocks):** Verified EUR to USD amount/rate/timestamp using explicit demo data and provider mocks; invalid inputs and missing keys return safe errors without credentials. A live provider quote was intentionally not requested because the submission is being kept key-free.
- [ ] After Checkpoint 2 passes, make a short commit: `Section 2: ExchangeRate API done`.

## 3. SQLite persistence and history
- [x] Create SQLite schema and startup initialization for conversion history, favorite currency pairs, and daily rate snapshots.
- [x] Persist successful conversions and provide endpoints to list recent history and clear it.
- [x] Save, list, and remove favorite pairs with duplicate handling.
- [x] Store one daily snapshot per base currency when rates are fetched; keep missing dates absent rather than fabricating history.

**Checkpoint 3 - PASSED:** Persistence tests use a temporary SQLite database, verify conversions and favorites including duplicate handling, check daily snapshot upsert and absent dates, and confirm saved data survives a FastAPI restart.
- [ ] After Checkpoint 3 passes, make a short commit: `Section 3: SQLite persistence done`.

## 4. Historical trend API and chart
- [x] Add a history endpoint for a currency pair and requested 7-, 30-, or 90-day range.
- [x] Normalize provider and snapshot data into dated rate points, clearly indicate data gaps, and handle insufficient history without crashing.
- [x] Add a lightweight responsive chart below the converter with 7/30/90-day controls and clear date/rate axes.

**Checkpoint 4 - PASSED:** All three ranges are validated; snapshots preserve gaps, empty history has an explicit state, a single point has a marker, and demo charts render multiple points. Browser checks covered 7/30/90 days and narrow/desktop layouts without overflow.
- [ ] After Checkpoint 4 passes, make a short commit: `Section 4: historical trends done`.

## 5. Converter interface and live conversion flow
- [x] Build the OANDA-inspired minimal converter screen with prominent amount input, source/target currency selectors, clear converted output, swap action, loading/error states, and a trend chart below.
- [x] Populate selectors from the backend currency list and refresh the result when amount or either currency changes, with debouncing where appropriate.
- [x] Show the effective rate and data timestamp near the result; keep keyboard and screen-reader interaction usable.

**Checkpoint 5 - PASSED (keyless demo):** Browser checks verified amount changes, swapping, safe invalid-input/provider-error states, timestamps, and the 320px layout. Live provider behavior is covered by backend mocks; no real key was used.
- [ ] After Checkpoint 5 passes, make a short commit: `Section 5: converter interface done`.

## 6. Conversion history, favorites, and travel budgeting
- [x] Add a recent-conversions view backed by SQLite, with a way to reselect a prior pair and clear history.
- [x] Add favorite-pair controls backed by SQLite, including add/remove and quick selection.
- [x] Add a Travel Budgeting toggle. When enabled, accept one base amount and show conversions to USD, EUR, GBP, JPY, and AUD in a comparison table; when disabled, return to the standard single-pair workflow.
- [x] Handle a base currency that is also one of the five targets and partial provider failures clearly.

**Checkpoint 6 - PASSED (keyless demo):** Browser/API checks verified favorite add/remove and persistence, conversion history and clearing, all five budget targets (including the base currency), switching back to single-pair mode, and safe errors.
- [ ] After Checkpoint 6 passes, make a short commit: `Section 6: favorites and travel budgeting done`.

## 7. End-to-end hardening and run documentation
- [x] Add focused backend tests and browser coverage for the primary user flows, API failures, and persistence behavior.
- [x] Verify local proxy/configuration, ensure secrets and database files are ignored, and review error messages for credential disclosure.
- [x] Document prerequisites, keyless demo setup, local `.env` creation using `.env.example`, live-key setup, database behavior, and commands to run tests and both services.
- [x] Confirm `.gitignore` excludes `.env` and SQLite files, README explains how to run the app, and no real API key appears in repository files or commit history.

**Checkpoint 7 - PASSED (keyless demo):** Installed dependencies, built the frontend, passed backend tests, ran both services in demo mode, exercised conversion/chart/favorites/history/travel-budget flows, and verified no `.env` or database file is tracked. Live API access remains optional and was not tested.
- [ ] After Checkpoint 7 passes, make a short commit: `Section 7: end-to-end hardening done`.
