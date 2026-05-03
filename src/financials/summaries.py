from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from financials.calculators.housing import money
from financials.scenario import get_scenario_id

MONTHS_PER_YEAR = Decimal("12")
WEEKS_PER_YEAR = Decimal("52")


@dataclass(frozen=True)
class ManualSummaryItem:
    scope: str
    category: str
    amount: Decimal
    frequency: str
    notes: str = ""
    id: int | None = None


@dataclass(frozen=True)
class HouseholdSummary:
    monthly_income: Decimal
    monthly_expenses: Decimal
    monthly_savings: Decimal
    monthly_net: Decimal


def monthly_amount(amount: Decimal, frequency: str) -> Decimal:
    normalised = frequency.strip().lower()
    if normalised == "monthly":
        return money(amount)
    if normalised == "weekly":
        return money(amount * WEEKS_PER_YEAR / MONTHS_PER_YEAR)
    if normalised == "yearly":
        return money(amount / MONTHS_PER_YEAR)
    if normalised == "one_off":
        return Decimal("0.00")
    raise ValueError(f"Unsupported frequency: {frequency}")


def add_manual_summary(
    connection: sqlite3.Connection,
    scenario_name: str,
    scope: str,
    category: str,
    amount: Decimal,
    frequency: str,
    notes: str = "",
) -> int:
    scenario_id = get_scenario_id(connection, scenario_name)
    cursor = connection.execute(
        """
        INSERT INTO manual_summary (scenario_id, scope, category, amount, frequency, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (scenario_id, scope, category, str(amount), frequency, notes),
    )
    connection.commit()
    return int(cursor.lastrowid)


def list_manual_summaries(connection: sqlite3.Connection, scenario_name: str) -> list[ManualSummaryItem]:
    scenario_id = get_scenario_id(connection, scenario_name)
    rows = connection.execute(
        """
        SELECT id, scope, category, amount, frequency, notes
        FROM manual_summary
        WHERE scenario_id = ?
        ORDER BY scope, category, id
        """,
        (scenario_id,),
    ).fetchall()
    return [
        ManualSummaryItem(
            scope=row["scope"],
            category=row["category"],
            amount=Decimal(row["amount"]),
            frequency=row["frequency"],
            notes=row["notes"],
            id=row["id"],
        )
        for row in rows
    ]


def delete_manual_summary(connection: sqlite3.Connection, summary_id: int) -> None:
    connection.execute("DELETE FROM manual_summary WHERE id = ?", (summary_id,))
    connection.commit()


def calculate_household_summary(items: list[ManualSummaryItem]) -> HouseholdSummary:
    monthly_income = Decimal("0.00")
    monthly_expenses = Decimal("0.00")
    monthly_savings = Decimal("0.00")

    for item in items:
        amount = monthly_amount(item.amount, item.frequency)
        scope = item.scope.strip().lower()
        if scope == "income":
            monthly_income += amount
        elif scope == "expense":
            monthly_expenses += amount
        elif scope == "saving":
            monthly_savings += amount
        else:
            raise ValueError(f"Unsupported manual summary scope: {item.scope}")

    return HouseholdSummary(
        monthly_income=money(monthly_income),
        monthly_expenses=money(monthly_expenses),
        monthly_savings=money(monthly_savings),
        monthly_net=money(monthly_income - monthly_expenses - monthly_savings),
    )
