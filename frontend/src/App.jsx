import { lazy, Suspense, useEffect, useState } from 'react';
import {
  ArrowDownUp,
  ArrowRight,
  Heart,
  RefreshCw,
  WalletCards,
  X,
} from 'lucide-react';

const RateChart = lazy(() => import('./RateChart.jsx'));

const RANGE_OPTIONS = [7, 30, 90];

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = typeof body.detail === 'string' ? body.detail : message;
    } catch {
      // Keep the status message for non-JSON responses.
    }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function currencyAmount(value, currency, maximumFractionDigits = 2) {
  if (!Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat('en', {
    style: 'currency',
    currency,
    maximumFractionDigits,
  }).format(Number(value));
}

function numberValue(value, maximumFractionDigits = 6) {
  return new Intl.NumberFormat('en', { maximumFractionDigits }).format(Number(value));
}

export default function App() {
  const [currencies, setCurrencies] = useState([]);
  const [source, setSource] = useState('EUR');
  const [target, setTarget] = useState('USD');
  const [amount, setAmount] = useState('1');
  const [budgetMode, setBudgetMode] = useState(false);
  const [range, setRange] = useState(30);
  const [quote, setQuote] = useState(null);
  const [budget, setBudget] = useState(null);
  const [history, setHistory] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [trend, setTrend] = useState({ observations: [], data_source: 'none' });
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState('');
  const [quoteError, setQuoteError] = useState('');
  const [favoriteError, setFavoriteError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    request('/api/currencies', { signal: controller.signal })
      .then(({ currencies: list }) => {
        setCurrencies(list);
        if (!list.some(({ code }) => code === 'EUR')) setSource(list[0]?.code ?? 'USD');
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setPageError(error.message);
      });
    request('/api/favorites', { signal: controller.signal })
      .then(({ favorites: list }) => setFavorites(list))
      .catch(() => {});
    request('/api/history?limit=6', { signal: controller.signal })
      .then(({ conversions }) => setHistory(conversions))
      .catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!currencies.length || !RANGE_OPTIONS.includes(range)) return undefined;
    const controller = new AbortController();
    const query = new URLSearchParams({ from: source, to: target, days: String(range) });
    request(`/api/rates/history?${query}`, { signal: controller.signal })
      .then(setTrend)
      .catch((error) => {
        if (error.name !== 'AbortError') setTrend({ observations: [], data_source: 'none' });
      });
    return () => controller.abort();
  }, [currencies, range, source, target]);

  useEffect(() => {
    if (!currencies.length) return undefined;
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setQuote(null);
      setBudget(null);
      setQuoteError(amount ? 'Enter an amount greater than zero.' : '');
      setLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    const query = new URLSearchParams({ from: source, amount });
    if (!budgetMode) query.set('to', target);
    setQuote(null);
    setBudget(null);
    setQuoteError('');
    setLoading(true);

    const timer = window.setTimeout(async () => {
      try {
        const result = await request(
          `/api/convert/${budgetMode ? 'budget' : ''}?${query}`.replace('/?', '?'),
          { signal: controller.signal },
        );
        if (budgetMode) setBudget(result);
        else setQuote(result);
        setQuoteError('');
        request('/api/history?limit=6')
          .then(({ conversions }) => setHistory(conversions))
          .catch(() => {});
      } catch (error) {
        if (error.name !== 'AbortError') setQuoteError(error.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 220);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [amount, budgetMode, currencies, source, target]);

  const currencyName = (code) => currencies.find((currency) => currency.code === code)?.name ?? code;
  const currentDataSource = budget?.data_source ?? quote?.data_source;
  const isDemo = currentDataSource === 'demo' || trend.data_source === 'demo';
  const currentFavorite = favorites.some(
    (favorite) => favorite.source_currency === source && favorite.target_currency === target,
  );

  function swapCurrencies() {
    setSource(target);
    setTarget(source);
  }

  async function toggleFavorite() {
    setFavoriteError('');
    try {
      if (currentFavorite) {
        await request(`/api/favorites/${source}/${target}`, { method: 'DELETE' });
      } else {
        await request('/api/favorites', {
          method: 'POST',
          body: JSON.stringify({ source_currency: source, target_currency: target }),
        });
      }
      const result = await request('/api/favorites');
      setFavorites(result.favorites);
    } catch (error) {
      setFavoriteError(error.message);
    }
  }

  async function clearHistory() {
    await request('/api/history', { method: 'DELETE' });
    setHistory([]);
  }

  function selectPair(pair, priorAmount = amount) {
    setSource(pair.source_currency);
    setTarget(pair.target_currency);
    setAmount(String(priorAmount));
    setBudgetMode(false);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="Ratefield home">
          <span className="wordmark-mark">R</span>
          <span>ratefield</span>
        </a>
        <div className="topbar-right">
          <span className={`connection-label ${isDemo ? 'is-demo' : ''}`}>
            <span className="connection-dot" />
            {isDemo ? 'Sample rates' : 'Rate desk'}
          </span>
          <span className="topbar-date">CURRENCY CONVERTER</span>
        </div>
      </header>

      <main id="top">
        <section className="page-heading" aria-labelledby="page-title">
          <div>
            <p className="eyebrow">Exchange rates, made clear</p>
            <h1 id="page-title">Currency converter</h1>
          </div>
          <label className={`mode-toggle ${budgetMode ? 'active' : ''}`}>
            <input
              type="checkbox"
              checked={budgetMode}
              onChange={(event) => setBudgetMode(event.target.checked)}
            />
            <span className="toggle-track" aria-hidden="true"><span /></span>
            <WalletCards size={17} strokeWidth={1.8} />
            <span>Travel budget</span>
          </label>
        </section>

        {isDemo && (
          <div className="demo-notice" role="status">
            Sample mode: quotes and chart movement are illustrative, not live market data.
          </div>
        )}
        {pageError && <div className="alert" role="alert">{pageError}</div>}

        <section className="converter-panel" aria-label="Currency conversion">
          <div className="converter-topline">
            <span>{budgetMode ? 'ONE AMOUNT, FIVE CURRENCIES' : 'CONVERT AMOUNT'}</span>
            <button
              className={`icon-action favorite-action ${currentFavorite ? 'selected' : ''}`}
              onClick={toggleFavorite}
              aria-label={currentFavorite ? 'Remove favorite pair' : 'Save pair as favorite'}
              title={currentFavorite ? 'Remove favorite pair' : 'Save pair'}
              disabled={budgetMode}
            >
              <Heart size={18} fill={currentFavorite ? 'currentColor' : 'none'} />
              <span>{currentFavorite ? 'Saved pair' : 'Save pair'}</span>
            </button>
          </div>

          <div className="conversion-grid">
            <div className="currency-field">
              <label htmlFor="amount">You have</label>
              <div className="field-row">
                <input
                  id="amount"
                  className="amount-input"
                  type="number"
                  min="0"
                  step="any"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  inputMode="decimal"
                  aria-label="Amount to convert"
                />
                <label className="select-wrap" htmlFor="source-currency">
                  <span className="sr-only">Source currency</span>
                  <select id="source-currency" value={source} onChange={(event) => setSource(event.target.value)}>
                    {currencies.map(({ code }) => <option key={code} value={code}>{code}</option>)}
                  </select>
                  <small>{currencyName(source)}</small>
                </label>
              </div>
            </div>

            <button className="swap-button" onClick={swapCurrencies} aria-label="Swap currencies" title="Swap currencies">
              <ArrowDownUp size={18} />
            </button>

            <div className={`currency-field result-field ${budgetMode ? 'budget-result' : ''}`}>
              <label>{budgetMode ? 'Travel budget comparison' : 'You receive'}</label>
              {budgetMode ? (
                <div className="budget-summary">
                  <strong>{amount && Number(amount) > 0 ? currencyAmount(amount, source) : '—'}</strong>
                  <span>starting in {source}</span>
                </div>
              ) : (
                <div className="field-row">
                  <output className="amount-output" aria-live="polite">
                    {quote ? currencyAmount(quote.converted_amount, target) : loading ? '…' : '—'}
                  </output>
                  <label className="select-wrap" htmlFor="target-currency">
                    <span className="sr-only">Target currency</span>
                    <select id="target-currency" value={target} onChange={(event) => setTarget(event.target.value)}>
                      {currencies.map(({ code }) => <option key={code} value={code}>{code}</option>)}
                    </select>
                    <small>{currencyName(target)}</small>
                  </label>
                </div>
              )}
            </div>
          </div>

          {budgetMode && (
            <div className="budget-table-wrap">
              <table className="budget-table">
                <thead><tr><th>Currency</th><th>Rate</th><th className="align-right">You receive</th></tr></thead>
                <tbody>
                  {(budget?.results ?? ['USD', 'EUR', 'GBP', 'JPY', 'AUD'].map((currency) => ({ currency }))).map((row) => (
                    <tr key={row.currency}>
                      <td><strong>{row.currency}</strong><span>{currencyName(row.currency)}</span></td>
                      <td>{row.rate ? `${numberValue(row.rate)} ${row.currency}` : loading ? '…' : '—'}</td>
                      <td className="align-right result-value">
                        {row.converted_amount != null ? currencyAmount(row.converted_amount, row.currency) : row.error ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="conversion-foot">
            <div className="quote-meta" aria-live="polite">
              {loading ? <><RefreshCw size={14} className="spin" /> Updating rate</> : quote ? (
                <>{`1 ${source} = ${numberValue(quote.rate)} ${target}`}<span className="meta-divider">·</span>{quote.timestamp}</>
              ) : budget ? (
                <>{`${budget.amount} ${source} compared across five currencies`}<span className="meta-divider">·</span>{budget.timestamp}</>
              ) : 'Rates update when you change an amount or currency.'}
            </div>
            <div className="conversion-actions">
              {quoteError && <span className="inline-error" role="alert">{quoteError}</span>}
              <button className="text-action" onClick={() => { setAmount('1'); }}>
                <RefreshCw size={14} /> Reset
              </button>
            </div>
          </div>
        </section>

        <section className="trend-section" aria-labelledby="trend-title">
          <div className="section-heading trend-heading">
            <div>
              <p className="eyebrow">Rate movement</p>
              <h2 id="trend-title">{source} to {target}</h2>
            </div>
            <div className="range-control" role="group" aria-label="Chart time range">
              {RANGE_OPTIONS.map((days) => (
                <button key={days} className={range === days ? 'active' : ''} onClick={() => setRange(days)} aria-pressed={range === days}>
                  {days}D
                </button>
              ))}
            </div>
          </div>
          <div className="trend-legend">
            <span className="legend-line" />
            <span>1 {source} in {target}</span>
            {trend.data_source === 'demo' && <span className="sample-tag">ILLUSTRATIVE</span>}
            {trend.data_source === 'live' && <span className="sample-tag live-tag">SAVED DAILY RATES</span>}
          </div>
          <div className="chart-wrap">
            {trend.observations.length ? (
              <Suspense fallback={<div className="chart-loading">Loading rate chart…</div>}>
                <RateChart observations={trend.observations} source={source} />
              </Suspense>
            ) : (
              <div className="empty-chart">
                <div className="empty-chart-mark"><ArrowRight size={20} /></div>
                <strong>No saved rate history yet</strong>
                <span>Daily points appear after live rates are fetched. Missing dates stay blank.</span>
              </div>
            )}
          </div>
          <p className="chart-note">Indicative exchange rates. Historical observations depend on saved daily quotes.</p>
        </section>

        <section className="lists-section">
          <div className="list-column">
            <div className="section-heading compact-heading">
              <div><p className="eyebrow">Quick access</p><h2>Favorite pairs</h2></div>
              <Heart size={17} strokeWidth={1.7} />
            </div>
            {favorites.length ? (
              <ul className="pair-list">
                {favorites.map((pair) => (
                  <li key={pair.id}>
                    <button className="pair-select" onClick={() => selectPair(pair)}>
                      <span className="pair-codes">{pair.source_currency}<ArrowRight size={14} />{pair.target_currency}</span>
                      <span className="pair-names">{currencyName(pair.source_currency)} to {currencyName(pair.target_currency)}</span>
                    </button>
                    <button className="remove-button" onClick={async () => {
                      await request(`/api/favorites/${pair.source_currency}/${pair.target_currency}`, { method: 'DELETE' });
                      setFavorites((items) => items.filter((item) => item.id !== pair.id));
                    }} aria-label={`Remove ${pair.source_currency} to ${pair.target_currency}`}><X size={15} /></button>
                  </li>
                ))}
              </ul>
            ) : <p className="empty-list">Save a pair with the heart above for quick access.</p>}
            {favoriteError && <p className="inline-error">{favoriteError}</p>}
          </div>

          <div className="list-column history-column">
            <div className="section-heading compact-heading">
              <div><p className="eyebrow">Your activity</p><h2>Recent conversions</h2></div>
              {history.length > 0 && <button className="text-action clear-action" onClick={clearHistory}>Clear</button>}
            </div>
            {history.length ? (
              <ul className="history-list">
                {history.slice(0, 5).map((item) => (
                  <li key={item.id}>
                    <button className="history-select" onClick={() => selectPair(item, item.amount)}>
                      <span className="history-pair">{item.source_currency}<ArrowRight size={13} />{item.target_currency}</span>
                      <span className="history-amount">{currencyAmount(item.converted_amount, item.target_currency)}</span>
                    </button>
                    <span className="history-date">{new Date(item.timestamp).toLocaleDateString('en', { month: 'short', day: 'numeric' })}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="empty-list">Completed conversions will show here.</p>}
          </div>
        </section>

        <footer className="page-footer">
          <span>RATEFIELD <span className="footer-dot">·</span> CURRENCY TOOLS</span>
          <span>{isDemo ? 'DEMO DATA' : 'EXCHANGERATE-API'}</span>
        </footer>
      </main>
    </div>
  );
}
