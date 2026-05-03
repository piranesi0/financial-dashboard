from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AssumptionValue:
    namespace: str
    key: str
    value: str
    value_type: str
    unit: str
    source: str


def get_scenario_id(connection: sqlite3.Connection, name: str) -> int:
    row = connection.execute(
        "SELECT id FROM scenario WHERE name = ?",
        (name,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Scenario not found: {name}")
    return int(row["id"])


def create_scenario(connection: sqlite3.Connection, name: str, description: str = "") -> int:
    connection.execute(
        """
        INSERT INTO scenario (name, description)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET description = excluded.description
        """,
        (name, description),
    )
    connection.commit()
    return get_scenario_id(connection, name)


def list_scenarios(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id, name, description, created_at FROM scenario ORDER BY name"
    ).fetchall()


def set_assumption(
    connection: sqlite3.Connection,
    scenario_name: str,
    namespace: str,
    key: str,
    value: str,
    value_type: str = "text",
    unit: str = "",
    source: str = "manual",
) -> None:
    scenario_id = get_scenario_id(connection, scenario_name)
    connection.execute(
        """
        INSERT INTO assumption (scenario_id, namespace, key, value, value_type, unit, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scenario_id, namespace, key) DO UPDATE SET
            value = excluded.value,
            value_type = excluded.value_type,
            unit = excluded.unit,
            source = excluded.source
        """,
        (scenario_id, namespace, key, value, value_type, unit, source),
    )
    connection.commit()


def get_assumptions(connection: sqlite3.Connection, scenario_name: str) -> dict[tuple[str, str], AssumptionValue]:
    scenario_id = get_scenario_id(connection, scenario_name)
    rows = connection.execute(
        """
        SELECT namespace, key, value, value_type, unit, source
        FROM assumption
        WHERE scenario_id = ?
        ORDER BY namespace, key
        """,
        (scenario_id,),
    ).fetchall()
    return {
        (row["namespace"], row["key"]): AssumptionValue(
            namespace=row["namespace"],
            key=row["key"],
            value=row["value"],
            value_type=row["value_type"],
            unit=row["unit"],
            source=row["source"],
        )
        for row in rows
    }


def assumption_text(assumptions: dict[tuple[str, str], AssumptionValue], namespace: str, key: str) -> str:
    try:
        return assumptions[(namespace, key)].value
    except KeyError as exc:
        raise ValueError(f"Missing assumption: {namespace}.{key}") from exc


def assumption_decimal(assumptions: dict[tuple[str, str], AssumptionValue], namespace: str, key: str) -> Decimal:
    return Decimal(assumption_text(assumptions, namespace, key))


def assumption_int(assumptions: dict[tuple[str, str], AssumptionValue], namespace: str, key: str) -> int:
    return int(assumption_text(assumptions, namespace, key))


def assumption_bool(assumptions: dict[tuple[str, str], AssumptionValue], namespace: str, key: str) -> bool:
    value = assumption_text(assumptions, namespace, key).strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean assumption: {namespace}.{key}={value}")
