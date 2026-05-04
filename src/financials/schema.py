from __future__ import annotations

import sqlite3
from pathlib import Path

# When the database path is the special sentinel ":memory:", all connections
# use this shared-cache URI so that every thread sees the same in-memory DB.
# The URI name "financials_mem" is arbitrary but must be consistent.
_MEMORY_SENTINEL = ":memory:"
_SHARED_MEMORY_URI = "file:financials_mem?mode=memory&cache=shared"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_file (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workbook_sheet (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_file(id),
    name TEXT NOT NULL,
    used_rows INTEGER NOT NULL,
    used_columns INTEGER NOT NULL,
    non_empty_cells INTEGER NOT NULL,
    formula_count INTEGER NOT NULL,
    UNIQUE(source_file_id, name)
);

CREATE TABLE IF NOT EXISTS scenario (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assumption (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenario(id),
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'text',
    unit TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    UNIQUE(scenario_id, namespace, key)
);

CREATE TABLE IF NOT EXISTS manual_summary (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenario(id),
    scope TEXT NOT NULL,
    category TEXT NOT NULL,
    amount TEXT NOT NULL,
    frequency TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    group_name TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS transaction_raw (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_file(id),
    sheet_name TEXT NOT NULL,
    row_number INTEGER NOT NULL,
    transaction_id TEXT,
    transaction_date TEXT,
    transaction_time TEXT,
    type TEXT,
    name TEXT,
    category TEXT,
    amount TEXT,
    local_amount TEXT,
    currency TEXT,
    local_currency TEXT,
    notes TEXT,
    description TEXT,
    raw_json TEXT NOT NULL,
    UNIQUE(source_file_id, sheet_name, row_number)
);

CREATE TABLE IF NOT EXISTS calculator_output (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenario(id),
    calculator TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _is_memory(path: str | Path) -> bool:
    return str(path) == _MEMORY_SENTINEL


def connect_database(path: str | Path) -> sqlite3.Connection:
    if _is_memory(path):
        # check_same_thread=False is intentional: each request opens its own
        # short-lived connection to the shared in-memory URI, so no single
        # connection is shared across threads.
        connection = sqlite3.connect(_SHARED_MEMORY_URI, check_same_thread=False, uri=True)
    else:
        connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database(path: str | Path) -> sqlite3.Connection:
    connection = connect_database(path)
    connection.executescript(SCHEMA_SQL)
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(assumption)").fetchall()
    }
    if "value_type" not in columns:
        connection.execute("ALTER TABLE assumption ADD COLUMN value_type TEXT NOT NULL DEFAULT 'text'")
    ms_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(manual_summary)").fetchall()
    }
    if "group_name" not in ms_columns:
        connection.execute("ALTER TABLE manual_summary ADD COLUMN group_name TEXT NOT NULL DEFAULT ''")
    connection.commit()
    return connection
