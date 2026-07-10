"""SQLite store for performance daily ledger and payback."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_ledger (
    date TEXT PRIMARY KEY,
    pv_kwh REAL,
    solcast_forecast_kwh REAL,
    forecast_accuracy_pct REAL,
    export_kwh REAL,
    import_kwh REAL,
    export_earnings_gbp REAL,
    import_spend_gbp REAL,
    avoided_grid_cost_gbp REAL,
    clipping_loss_kwh REAL,
    clipping_loss_valuation_gbp REAL,
    net_daily_savings_gbp REAL,
    peak_power_kw REAL,
    peak_vs_rated_pct REAL,
    virtual_temp_min_c REAL,
    virtual_temp_max_c REAL,
    wind_correlation_note TEXT
);

CREATE TABLE IF NOT EXISTS payback_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    install_cost_gbp REAL,
    install_date TEXT,
    system_rte REAL DEFAULT 0.85
);

CREATE TABLE IF NOT EXISTS hems_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_hems_events_ts ON hems_events(ts);
CREATE INDEX IF NOT EXISTS idx_hems_events_type ON hems_events(event_type);
"""


class PerformanceStore:
    """Queryable SQLite ledger per plant config entry."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    @property
    def path(self) -> Path:
        return self._path

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def init_schema(self) -> None:
        conn = self.connect()
        conn.executescript(_SCHEMA)
        conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def upsert_daily_ledger(self, row: dict[str, Any]) -> None:
        conn = self.connect()
        conn.execute(
            """
            INSERT INTO daily_ledger (
                date, pv_kwh, solcast_forecast_kwh, forecast_accuracy_pct,
                export_kwh, import_kwh, export_earnings_gbp, import_spend_gbp,
                avoided_grid_cost_gbp, clipping_loss_kwh, clipping_loss_valuation_gbp,
                net_daily_savings_gbp, peak_power_kw, peak_vs_rated_pct,
                virtual_temp_min_c, virtual_temp_max_c, wind_correlation_note
            ) VALUES (
                :date, :pv_kwh, :solcast_forecast_kwh, :forecast_accuracy_pct,
                :export_kwh, :import_kwh, :export_earnings_gbp, :import_spend_gbp,
                :avoided_grid_cost_gbp, :clipping_loss_kwh, :clipping_loss_valuation_gbp,
                :net_daily_savings_gbp, :peak_power_kw, :peak_vs_rated_pct,
                :virtual_temp_min_c, :virtual_temp_max_c, :wind_correlation_note
            )
            ON CONFLICT(date) DO UPDATE SET
                pv_kwh=excluded.pv_kwh,
                solcast_forecast_kwh=excluded.solcast_forecast_kwh,
                forecast_accuracy_pct=excluded.forecast_accuracy_pct,
                export_kwh=excluded.export_kwh,
                import_kwh=excluded.import_kwh,
                export_earnings_gbp=excluded.export_earnings_gbp,
                import_spend_gbp=excluded.import_spend_gbp,
                avoided_grid_cost_gbp=excluded.avoided_grid_cost_gbp,
                clipping_loss_kwh=excluded.clipping_loss_kwh,
                clipping_loss_valuation_gbp=excluded.clipping_loss_valuation_gbp,
                net_daily_savings_gbp=excluded.net_daily_savings_gbp,
                peak_power_kw=excluded.peak_power_kw,
                peak_vs_rated_pct=excluded.peak_vs_rated_pct,
                virtual_temp_min_c=excluded.virtual_temp_min_c,
                virtual_temp_max_c=excluded.virtual_temp_max_c,
                wind_correlation_note=excluded.wind_correlation_note
            """,
            row,
        )
        conn.commit()

    def get_daily_ledger(self, date: str) -> dict[str, Any] | None:
        conn = self.connect()
        row = conn.execute("SELECT * FROM daily_ledger WHERE date = ?", (date,)).fetchone()
        return dict(row) if row else None

    def sum_net_savings(self) -> float:
        conn = self.connect()
        row = conn.execute(
            "SELECT COALESCE(SUM(net_daily_savings_gbp), 0) AS total FROM daily_ledger"
        ).fetchone()
        return float(row["total"]) if row else 0.0

    def avg_net_savings_days(self, days: int = 90) -> float | None:
        conn = self.connect()
        row = conn.execute(
            """
            SELECT AVG(net_daily_savings_gbp) AS avg_net
            FROM daily_ledger
            WHERE date >= date('now', ?)
            """,
            (f"-{int(days)} days",),
        ).fetchone()
        if not row or row["avg_net"] is None:
            return None
        return float(row["avg_net"])

    def set_payback_config(
        self,
        *,
        install_cost_gbp: float | None,
        install_date: str | None = None,
        system_rte: float = 0.85,
    ) -> None:
        conn = self.connect()
        conn.execute(
            """
            INSERT INTO payback_config (id, install_cost_gbp, install_date, system_rte)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                install_cost_gbp=excluded.install_cost_gbp,
                install_date=excluded.install_date,
                system_rte=excluded.system_rte
            """,
            (install_cost_gbp, install_date, system_rte),
        )
        conn.commit()

    def get_payback_config(self) -> dict[str, Any]:
        conn = self.connect()
        row = conn.execute("SELECT * FROM payback_config WHERE id = 1").fetchone()
        return dict(row) if row else {}

    def log_event(self, *, ts: str, event_type: str, payload_json: str | None = None) -> None:
        conn = self.connect()
        conn.execute(
            "INSERT INTO hems_events (ts, event_type, payload_json) VALUES (?, ?, ?)",
            (ts, event_type, payload_json),
        )
        conn.commit()
