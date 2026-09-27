from datetime import date
from decimal import Decimal
from pathlib import Path

from backend.app.database import Database


def test_persistence_and_daily_snapshot_upsert(tmp_path: Path) -> None:
    database_path = tmp_path / "currency.sqlite3"
    database = Database(database_path)
    database.initialize()

    conversion_id = database.save_conversion(
        "EUR",
        "USD",
        Decimal("10"),
        Decimal("1.08"),
        Decimal("10.8"),
        "Sun, 27 Sep 2026 00:00:00 +0000",
    )
    favorite_id = database.add_favorite("EUR", "USD")
    duplicate_id = database.add_favorite("EUR", "USD")
    rates = {"EUR": Decimal("1"), "USD": Decimal("1.08")}
    snapshot_day = date(2026, 9, 27)
    database.save_daily_snapshot("EUR", snapshot_day, rates, "first update")
    database.save_daily_snapshot("EUR", snapshot_day, rates, "latest update")

    assert conversion_id > 0
    assert favorite_id is not None
    assert duplicate_id is None
    assert len(database.list_conversions()) == 1
    assert database.clear_conversions() == 1
    assert database.list_conversions() == []
    assert database.remove_favorite("EUR", "USD")
    assert database.list_favorites() == []

    reopened_database = Database(database_path)
    reopened_database.initialize()
    snapshots = reopened_database.list_daily_snapshots("EUR", snapshot_day, snapshot_day)

    assert len(snapshots) == 1
    assert snapshots[0]["timestamp"] == "latest update"
    assert snapshots[0]["rates"] == {"EUR": "1", "USD": "1.08"}
    assert reopened_database.list_daily_snapshots(
        "EUR", date(2026, 9, 28), date(2026, 9, 29)
    ) == []