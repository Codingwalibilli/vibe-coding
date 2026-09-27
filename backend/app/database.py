import json
import os
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .settings import PROJECT_ROOT

DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "currency.sqlite3"


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        configured_path = path or os.getenv("DATABASE_PATH") or DEFAULT_DATABASE_PATH
        self.path = Path(configured_path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_currency TEXT NOT NULL,
                    target_currency TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    rate TEXT NOT NULL,
                    converted_amount TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data_source TEXT NOT NULL DEFAULT 'live'
                );
                CREATE INDEX IF NOT EXISTS idx_conversions_timestamp
                    ON conversions(timestamp DESC);

                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_currency TEXT NOT NULL,
                    target_currency TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_currency, target_currency)
                );

                CREATE TABLE IF NOT EXISTS daily_snapshots (
                    base_currency TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    rates_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY(base_currency, snapshot_date)
                );
                """
            )
            conversion_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(conversions)")
            }
            if "data_source" not in conversion_columns:
                connection.execute(
                    "ALTER TABLE conversions ADD COLUMN data_source TEXT NOT NULL DEFAULT 'live'"
                )

    def save_conversion(
        self,
        source_currency: str,
        target_currency: str,
        amount: Decimal,
        rate: Decimal,
        converted_amount: Decimal,
        timestamp: str,
        data_source: str = "live",
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO conversions
                   (source_currency, target_currency, amount, rate, converted_amount, timestamp,
                    data_source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    source_currency,
                    target_currency,
                    str(amount),
                    str(rate),
                    str(converted_amount),
                    timestamp,
                    data_source,
                ),
            )
            return int(cursor.lastrowid)

    def list_conversions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM conversions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_conversions(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM conversions")
            return cursor.rowcount

    def add_favorite(self, source_currency: str, target_currency: str) -> int | None:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO favorites
                   (source_currency, target_currency, created_at) VALUES (?, ?, ?)""",
                (source_currency, target_currency, created_at),
            )
            return int(cursor.lastrowid) if cursor.rowcount else None

    def list_favorites(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM favorites ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def remove_favorite(self, source_currency: str, target_currency: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM favorites WHERE source_currency = ? AND target_currency = ?",
                (source_currency, target_currency),
            )
            return cursor.rowcount > 0

    def save_daily_snapshot(
        self,
        base_currency: str,
        snapshot_date: date,
        rates: dict[str, Decimal],
        timestamp: str,
    ) -> None:
        rates_json = json.dumps({code: str(rate) for code, rate in rates.items()})
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO daily_snapshots
                   (base_currency, snapshot_date, rates_json, timestamp)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(base_currency, snapshot_date) DO UPDATE SET
                     rates_json = excluded.rates_json,
                     timestamp = excluded.timestamp""",
                (base_currency, snapshot_date.isoformat(), rates_json, timestamp),
            )

    def list_daily_snapshots(
        self, base_currency: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT base_currency, snapshot_date, rates_json, timestamp
                   FROM daily_snapshots
                   WHERE base_currency = ? AND snapshot_date BETWEEN ? AND ?
                   ORDER BY snapshot_date""",
                (base_currency, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        snapshots = []
        for row in rows:
            record = dict(row)
            record["rates"] = json.loads(record.pop("rates_json"))
            snapshots.append(record)
        return snapshots

    def list_pair_snapshots(
        self, source_currency: str, target_currency: str, start_date: date, end_date: date
    ) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT base_currency, snapshot_date, rates_json, timestamp
                   FROM daily_snapshots
                   WHERE base_currency IN (?, ?) AND snapshot_date BETWEEN ? AND ?
                   ORDER BY snapshot_date""",
                (
                    source_currency,
                    target_currency,
                    start_date.isoformat(),
                    end_date.isoformat(),
                ),
            ).fetchall()

        rates_by_date: dict[str, tuple[Decimal, str, bool]] = {}
        for row in rows:
            rates = json.loads(row["rates_json"])
            base_currency = row["base_currency"]
            is_direct = base_currency == source_currency
            if is_direct:
                raw_rate = rates.get(target_currency)
                rate = Decimal(raw_rate) if raw_rate is not None else None
            else:
                raw_inverse = rates.get(source_currency)
                inverse = Decimal(raw_inverse) if raw_inverse is not None else None
                rate = Decimal("1") / inverse if inverse and inverse > 0 else None

            if rate is None or rate <= 0:
                continue
            snapshot_date = row["snapshot_date"]
            existing = rates_by_date.get(snapshot_date)
            if existing is None or is_direct:
                rates_by_date[snapshot_date] = (rate, row["timestamp"], is_direct)

        return [
            {"date": day, "rate": str(rate), "timestamp": timestamp}
            for day, (rate, timestamp, _) in sorted(rates_by_date.items())
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        return connection