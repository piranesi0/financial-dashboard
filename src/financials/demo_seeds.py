"""Demo scenario seed for the GitHub Pages static preview.

Uses fictional but plausible UK household figures — safe to publish publicly.
The scenario is named "demo" to distinguish it from the real "baseline".
"""
from __future__ import annotations

import sqlite3
from decimal import Decimal

from financials.scenario import get_scenario_id

DEMO_SCENARIO_NAME = "demo"

# ---------------------------------------------------------------------------
# Assumptions
# ---------------------------------------------------------------------------

DEMO_ASSUMPTIONS: list[tuple[str, str, str, str, str]] = [
    # -- Housing --
    ("housing", "flat_mortgage_balance", "260000", "money", "GBP"),
    ("housing", "flat_sale_price_low", "295000", "money", "GBP"),
    ("housing", "flat_sale_price_high", "325000", "money", "GBP"),
    ("housing", "estate_agent_fee_rate", "0.0125", "percent", "ratio"),
    ("housing", "solicitor_fee", "3500", "money", "GBP"),
    ("housing", "current_rent_income", "1150", "money", "GBP/month"),
    ("housing", "current_mortgage_payment", "1130", "money", "GBP/month"),
    ("housing", "house_price_low", "320000", "money", "GBP"),
    ("housing", "house_price_high", "460000", "money", "GBP"),
    ("housing", "default_deposit_rate", "0.10", "percent", "ratio"),
    ("housing", "default_mortgage_rate", "0.045", "percent", "ratio"),
    ("housing", "default_combined_gross_income", "0", "money", "GBP/year"),
    ("housing", "mortgage_term_years", "25", "integer", "years"),
    ("housing", "affordability_income_multiple_low", "4.0", "decimal", "multiple"),
    ("housing", "affordability_income_multiple_high", "4.5", "decimal", "multiple"),
    # -- Income: Person B (part-time, flexible schedule) --
    ("income", "charly_hourly_rate", "22.00", "money", "GBP/hour"),
    ("income", "charly_tax_code", "1257L", "text", ""),
    ("income", "charly_personal_allowance", "12570", "money", "GBP/year"),
    ("income", "charly_pension_contribution_rate", "0.05", "percent", "ratio"),
    ("income", "charly_income_tax_basic_rate", "0.20", "percent", "ratio"),
    ("income", "charly_income_tax_higher_rate", "0.40", "percent", "ratio"),
    ("income", "charly_income_tax_additional_rate", "0.45", "percent", "ratio"),
    ("income", "charly_basic_rate_limit", "37700", "money", "GBP/year"),
    ("income", "charly_higher_rate_threshold", "125140", "money", "GBP/year"),
    ("income", "charly_ni_primary_threshold", "12570", "money", "GBP/year"),
    ("income", "charly_ni_upper_earnings_limit", "50270", "money", "GBP/year"),
    ("income", "charly_ni_main_rate", "0.08", "percent", "ratio"),
    ("income", "charly_ni_upper_rate", "0.02", "percent", "ratio"),
    ("income", "charly_student_loan_threshold", "27295", "money", "GBP/year"),
    ("income", "charly_student_loan_rate", "0.09", "percent", "ratio"),
    # Flexible working (25 hrs/week) for the demo — more interesting than 0/mat-leave
    ("income", "charly_weekly_hours", "25", "decimal", "hours/week"),
    ("income", "charly_work_hours_part_time", "20", "decimal", "hours/week"),
    ("income", "charly_work_hours_full_time", "37.5", "decimal", "hours/week"),
    ("income", "charly_work_hours_flexible", "25", "decimal", "hours/week"),
    # -- Nursery --
    ("nursery", "enabled", "true", "boolean", ""),
    ("nursery", "daily_cost", "68.00", "money", "GBP/day"),
    ("nursery", "days_per_week", "3", "decimal", "days"),
    ("nursery", "weekly_funded_hours", "15", "decimal", "hours/week"),
    ("nursery", "hourly_cost", "8.50", "money", "GBP/hour"),
    ("nursery", "hours_per_day", "9", "decimal", "hours"),
    # -- Income: Person A (salaried) --
    ("income", "alex_baseline_year", "2026", "integer", "year"),
    ("income", "alex_base_salary_annual", "52000", "money", "GBP/year"),
    ("income", "alex_select_points", "9000", "decimal", "points/year"),
    ("income", "alex_select_point_value", "1", "money", "GBP/point"),
    ("income", "alex_pension_contribution_rate", "0.09", "percent", "ratio"),
    ("income", "alex_tax_code", "1257L", "text", ""),
    ("income", "alex_personal_allowance", "12570", "money", "GBP/year"),
    ("income", "alex_income_tax_basic_rate", "0.20", "percent", "ratio"),
    ("income", "alex_income_tax_higher_rate", "0.40", "percent", "ratio"),
    ("income", "alex_income_tax_additional_rate", "0.45", "percent", "ratio"),
    ("income", "alex_basic_rate_limit", "37700", "money", "GBP/year"),
    ("income", "alex_higher_rate_threshold", "125140", "money", "GBP/year"),
    ("income", "alex_ni_primary_threshold", "12570", "money", "GBP/year"),
    ("income", "alex_ni_upper_earnings_limit", "50270", "money", "GBP/year"),
    ("income", "alex_ni_main_rate", "0.08", "percent", "ratio"),
    ("income", "alex_ni_upper_rate", "0.02", "percent", "ratio"),
    ("income", "alex_student_loan_threshold", "27295", "money", "GBP/year"),
    ("income", "alex_student_loan_rate", "0.09", "percent", "ratio"),
    ("income", "alex_stock_gross_annual", "15000", "money", "GBP/year"),
    ("income", "alex_stock_net_annual", "6750", "money", "GBP/year"),
    ("income", "alex_include_stock_in_static_income", "false", "boolean", ""),
    # -- Categorisation --
    ("categorisation", "projects_scope", "personal", "text", ""),
    ("categorisation", "subscriptions_scope", "personal", "text", ""),
    ("categorisation", "faster_payments_scope", "internal_transfer", "text", ""),
    ("categorisation", "monzo_pots_scope", "budgeting", "text", ""),
    ("categorisation", "true_savings_count_as_outgoing", "false", "boolean", ""),
    # -- App --
    ("app", "mortgage_rate_options", "0.035,0.04,0.045,0.05", "list", "ratio"),
    ("app", "deposit_rate_options", "0.05,0.10,0.15", "list", "ratio"),
]

# ---------------------------------------------------------------------------
# Manual summaries (income / expenses / savings)
# ---------------------------------------------------------------------------

DEMO_SUMMARIES: list[tuple[str, str, str, str, str]] = [
    # scope, category, amount, frequency, group_name
    # -- Flat (rented out) --
    ("income", "Flat rental income", "1150.00", "monthly", "Flat"),
    ("expense", "Flat mortgage", "1130.00", "monthly", "Flat"),
    ("expense", "Flat buildings insurance", "29.00", "monthly", "Flat"),
    # -- Household bills --
    ("expense", "Council tax", "165.00", "monthly", "Bills"),
    ("expense", "Water", "45.00", "monthly", "Bills"),
    ("expense", "Gas & electric", "150.00", "monthly", "Bills"),
    ("expense", "Broadband", "35.00", "monthly", "Bills"),
    ("expense", "TV licence", "13.25", "monthly", "Bills"),
    ("expense", "Home insurance", "25.00", "monthly", "Bills"),
    # -- Personal bills --
    ("expense", "Car insurance", "55.00", "monthly", "Bills"),
    ("expense", "Car tax", "16.00", "monthly", "Bills"),
    ("expense", "Pet insurance", "32.00", "monthly", "Bills"),
    ("expense", "Life insurance", "14.00", "monthly", "Bills"),
    ("expense", "Mobile phones", "45.00", "monthly", "Bills"),
    ("expense", "Gym", "35.00", "monthly", "Personal"),
    ("expense", "Streaming services", "25.00", "monthly", "Bills"),
    ("expense", "Cloud storage", "9.00", "monthly", "Bills"),
    # -- Variable spending --
    ("expense", "Groceries", "650.00", "monthly", "Household"),
    ("expense", "Eating out", "200.00", "monthly", "Personal"),
    ("expense", "Personal care", "100.00", "monthly", "Personal"),
    ("expense", "Transport", "120.00", "monthly", "Bills"),
    ("expense", "Clothing", "60.00", "monthly", "Personal"),
    ("expense", "Entertainment", "80.00", "monthly", "Personal"),
    ("expense", "Baby / nursery", "50.00", "monthly", "Household"),
    # -- Savings --
    ("saving", "Emergency fund", "200.00", "monthly", "Savings"),
    ("saving", "Holiday fund", "100.00", "monthly", "Savings"),
]

DEMO_PLAN_SUMMARIES: list[tuple[str, str, str, str, str]] = [
    # scope, category, amount, frequency, group_name
    # -- Housing (Flat) --
    ("expense", "Mortgage", "1130.00", "monthly", "Housing-Flat"),
    ("expense", "Electricity", "80.00", "monthly", "Housing-Flat"),
    ("expense", "Gas", "60.00", "monthly", "Housing-Flat"),
    ("expense", "Water", "45.00", "monthly", "Housing-Flat"),
    ("expense", "Broadband", "35.00", "monthly", "Housing-Flat"),
    ("expense", "Council Tax", "165.00", "monthly", "Housing-Flat"),
    ("expense", "TV Licence", "14.00", "monthly", "Housing-Flat"),
    ("expense", "Home Insurance", "25.00", "monthly", "Housing-Flat"),
    ("expense", "Maintenance", "50.00", "monthly", "Housing-Flat"),
    # -- Housing (House) --
    ("expense", "Mortgage", "0.00", "monthly", "Housing-House"),
    ("expense", "Electricity", "80.00", "monthly", "Housing-House"),
    ("expense", "Gas", "60.00", "monthly", "Housing-House"),
    ("expense", "Water", "45.00", "monthly", "Housing-House"),
    ("expense", "Broadband", "35.00", "monthly", "Housing-House"),
    ("expense", "Council Tax", "180.00", "monthly", "Housing-House"),
    ("expense", "TV Licence", "14.00", "monthly", "Housing-House"),
    ("expense", "Home Insurance", "30.00", "monthly", "Housing-House"),
    ("expense", "Maintenance", "100.00", "monthly", "Housing-House"),
    # -- Obligations --
    ("expense", "Car Finance", "290.00", "monthly", "Obligations"),
    ("expense", "Phone (A)", "40.00", "monthly", "Obligations"),
    ("expense", "Phone (B)", "29.00", "monthly", "Obligations"),
    ("expense", "Life Insurance", "14.00", "monthly", "Obligations"),
    ("expense", "Car Insurance", "55.00", "monthly", "Obligations"),
    ("expense", "Pet Insurance", "32.00", "monthly", "Obligations"),
    # -- Living --
    ("expense", "Groceries", "800.00", "monthly", "Living"),
    ("expense", "Pet", "50.00", "monthly", "Living"),
    ("expense", "Fuel/Transit", "100.00", "monthly", "Living"),
    ("expense", "Household", "50.00", "monthly", "Living"),
    ("expense", "Personal Care", "50.00", "monthly", "Living"),
    ("expense", "Health", "0.00", "monthly", "Living"),
    ("expense", "Clothing", "60.00", "monthly", "Living"),
    ("expense", "Baby", "200.00", "monthly", "Living"),
    # -- Lifestyle --
    ("expense", "Subscriptions", "50.00", "monthly", "Lifestyle"),
    ("expense", "Dining Out", "100.00", "monthly", "Lifestyle"),
    ("expense", "Hobbies", "50.00", "monthly", "Lifestyle"),
    ("expense", "Fitness", "35.00", "monthly", "Lifestyle"),
    ("expense", "Travel", "50.00", "monthly", "Lifestyle"),
    ("expense", "Gifts", "30.00", "monthly", "Lifestyle"),
    # -- Sinking Funds --
    ("saving", "Emergency Fund", "200.00", "monthly", "Sinking Funds"),
    ("saving", "Car Maintenance", "50.00", "monthly", "Sinking Funds"),
    ("saving", "Renewals", "30.00", "monthly", "Sinking Funds"),
    ("saving", "Holiday Fund", "100.00", "monthly", "Sinking Funds"),
    ("saving", "Christmas", "50.00", "monthly", "Sinking Funds"),
]


def upsert_demo_scenario(connection: sqlite3.Connection) -> int:
    """Create (or refresh) the demo scenario with fictional but plausible data."""
    connection.execute(
        """
        INSERT INTO scenario (name, description)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET description = excluded.description
        """,
        (
            DEMO_SCENARIO_NAME,
            "Demo scenario — fictional data for the public GitHub Pages preview.",
        ),
    )
    scenario_id = connection.execute(
        "SELECT id FROM scenario WHERE name = ?",
        (DEMO_SCENARIO_NAME,),
    ).fetchone()["id"]

    connection.executemany(
        """
        INSERT INTO assumption (scenario_id, namespace, key, value, value_type, unit, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scenario_id, namespace, key) DO NOTHING
        """,
        [
            (scenario_id, namespace, key, value, value_type, unit, "demo_seed")
            for namespace, key, value, value_type, unit in DEMO_ASSUMPTIONS
        ],
    )

    _seed_summaries(connection, scenario_id, "seed:demo", DEMO_SUMMARIES)
    _seed_summaries(connection, scenario_id, "seed:demo:plan", DEMO_PLAN_SUMMARIES)
    connection.commit()
    return int(scenario_id)


def _seed_summaries(
    connection: sqlite3.Connection,
    scenario_id: int,
    note_prefix: str,
    rows: list[tuple[str, str, str, str, str]],
) -> None:
    already = connection.execute(
        "SELECT 1 FROM manual_summary WHERE scenario_id = ? AND notes LIKE ? LIMIT 1",
        (scenario_id, f"{note_prefix}%"),
    ).fetchone()
    if already:
        return
    connection.executemany(
        """
        INSERT INTO manual_summary (scenario_id, scope, category, amount, frequency, notes, group_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (scenario_id, scope, category, amount, frequency, f"{note_prefix}; demo value", group_name)
            for scope, category, amount, frequency, group_name in rows
        ],
    )
