from __future__ import annotations

import sqlite3
from pathlib import Path

from financials.xlsx import WorkbookProfile, profile_workbook


def persist_workbook_profile(connection: sqlite3.Connection, profile: WorkbookProfile) -> int:
    source_path = str(profile.path)
    connection.execute(
        """
        INSERT INTO source_file (path, kind)
        VALUES (?, ?)
        ON CONFLICT(path) DO UPDATE SET kind = excluded.kind
        """,
        (source_path, "xlsx"),
    )
    source_file_id = connection.execute(
        "SELECT id FROM source_file WHERE path = ?",
        (source_path,),
    ).fetchone()["id"]

    connection.executemany(
        """
        INSERT INTO workbook_sheet (
            source_file_id,
            name,
            used_rows,
            used_columns,
            non_empty_cells,
            formula_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_file_id, name) DO UPDATE SET
            used_rows = excluded.used_rows,
            used_columns = excluded.used_columns,
            non_empty_cells = excluded.non_empty_cells,
            formula_count = excluded.formula_count
        """,
        [
            (
                source_file_id,
                sheet.name,
                sheet.used_rows,
                sheet.used_columns,
                sheet.non_empty_cells,
                sheet.formula_count,
            )
            for sheet in profile.sheets
        ],
    )
    connection.commit()
    return int(source_file_id)


def profile_and_persist_workbook(connection: sqlite3.Connection, path: str | Path) -> int:
    return persist_workbook_profile(connection, profile_workbook(path))
