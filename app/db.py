"""SQLite persistence for operations analysis runs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from app.config import get_settings


class OpsRepository:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = Path(database_path or get_settings().database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _init_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ops_runs (
                    id TEXT PRIMARY KEY,
                    total_alarms INTEGER NOT NULL,
                    cluster_count INTEGER NOT NULL,
                    compression_ratio REAL NOT NULL,
                    overall_severity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_ops_created_at ON ops_runs(created_at DESC)"
            )

    def save_run(self, record: dict[str, Any]) -> None:
        payload = record.get("payload", record)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO ops_runs
                (id, total_alarms, cluster_count, compression_ratio,
                 overall_severity, created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    int(record["total_alarms"]),
                    int(record["cluster_count"]),
                    float(record["compression_ratio"]),
                    record["overall_severity"],
                    record["created_at"],
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT id, total_alarms, cluster_count, compression_ratio,
                       overall_severity, created_at
                FROM ops_runs ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload FROM ops_runs WHERE id = ?", (run_id,)
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def count(self) -> int:
        with closing(self._connect()) as connection, connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM ops_runs").fetchone()
        return int(row["n"])


_repository: OpsRepository | None = None


def get_repository() -> OpsRepository:
    global _repository
    if _repository is None:
        _repository = OpsRepository()
    return _repository
