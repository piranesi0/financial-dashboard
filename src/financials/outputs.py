from __future__ import annotations

import sqlite3
from decimal import Decimal
from typing import Mapping

from financials.scenario import get_scenario_id


def persist_calculator_outputs(
    connection: sqlite3.Connection,
    scenario_name: str,
    calculator: str,
    outputs: Mapping[str, tuple[Decimal | str | int, str]],
) -> None:
    scenario_id = get_scenario_id(connection, scenario_name)
    connection.execute(
        "DELETE FROM calculator_output WHERE scenario_id = ? AND calculator = ?",
        (scenario_id, calculator),
    )
    connection.executemany(
        """
        INSERT INTO calculator_output (scenario_id, calculator, key, value, unit)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (scenario_id, calculator, key, str(value), unit)
            for key, (value, unit) in outputs.items()
        ],
    )
    connection.commit()
