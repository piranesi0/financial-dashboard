from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

from financials.defaults import DEFAULTS
from financials.scenario import get_scenario_id

BASELINE_SCENARIO_NAME = "baseline"
SEEDED_EXPENSE_NOTE_PREFIX = "seed:example_outgoing"
SEEDED_BILLS_NOTE_PREFIX = "seed:finances2024"
SEEDED_PLAN_NOTE_PREFIX = "seed:plan"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_OUTGOING_PATH = PROJECT_ROOT / "sheets" / "example_outgoing.txt"

# Fixed bills and income seeded from Finances 2024.xlsx structure.
# Values are 2024 baselines — update them to current figures via the web UI.
BILLS_AND_INCOME_SEED: list[tuple[str, str, str, str, str]] = [
    # (scope, category, amount, frequency, group_name)
    # -- Flat (rented out) --
    ("income", "Flat rental income", "1144.00", "monthly", "Flat"),
    ("expense", "Flat mortgage", "1124.10", "monthly", "Flat"),
    ("expense", "Flat buildings insurance", "28.55", "monthly", "Flat"),
    # -- Household bills (current living situation) --
    ("expense", "Council tax", "165.00", "monthly", "Bills"),
    ("expense", "Water", "45.00", "monthly", "Bills"),
    ("expense", "Gas & electric", "150.00", "monthly", "Bills"),
    ("expense", "Broadband", "35.00", "monthly", "Bills"),
    ("expense", "TV licence", "13.25", "monthly", "Bills"),
    ("expense", "Home insurance", "25.00", "monthly", "Bills"),
    # -- Personal bills --
    ("expense", "Car insurance", "51.14", "monthly", "Bills"),
    ("expense", "Car tax", "15.75", "monthly", "Bills"),
    ("expense", "Pet insurance", "31.41", "monthly", "Bills"),
    ("expense", "Petplan", "21.00", "monthly", "Bills"),
    ("expense", "Life insurance", "13.82", "monthly", "Bills"),
    ("expense", "Mobile phone", "39.67", "monthly", "Bills"),
    ("expense", "Gym", "36.00", "monthly", "Personal"),
    ("expense", "Spotify", "10.99", "monthly", "Bills"),
    ("expense", "Cloud storage", "8.57", "monthly", "Bills"),
    ("expense", "Runna", "15.99", "monthly", "Personal"),
    ("expense", "Ring doorbell", "4.99", "monthly", "Bills"),
    ("expense", "Lloyds Platinum", "16.00", "monthly", "Bills"),
]

# Map example_outgoing categories to groups
CATEGORY_GROUP_MAP: dict[str, str] = {
    "Groceries": "Household",
    "Shopping": "Household",
    "Personal care": "Personal",
    "Treats": "Personal",
    "Eating out": "Personal",
    "Entertainment": "Personal",
    "Transport": "Bills",
    "Subscriptions": "Bills",
    "General": "Household",
    "Charity": "Personal",
    "Finances": "Bills",
    "Holidays": "Household",
    "Family": "Household",
    "Cash": "Personal",
    "Expenses": "Household",
}

# Budget plan seed data for the /plan page.
# Each tuple: (scope, category, amount, frequency, group_name)
# Housing items are split into Housing-Flat and Housing-House to support the
# living-situation tabs on the plan page.
PLAN_SEED: list[tuple[str, str, str, str, str]] = [
    # -- Housing (Flat) --
    ("expense", "Mortgage", "0.00", "monthly", "Housing-Flat"),
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
    ("expense", "Car Finance", "0.00", "monthly", "Obligations"),
    ("expense", "Phone (Alex)", "0.00", "monthly", "Obligations"),
    ("expense", "Phone (Charly)", "0.00", "monthly", "Obligations"),
    ("expense", "Life Insurance", "14.00", "monthly", "Obligations"),
    ("expense", "Car Insurance", "51.00", "monthly", "Obligations"),
    ("expense", "Pet Insurance", "31.00", "monthly", "Obligations"),
    # -- Living --
    ("expense", "Groceries", "600.00", "monthly", "Living"),
    ("expense", "Pet", "50.00", "monthly", "Living"),
    ("expense", "Fuel/Transit", "100.00", "monthly", "Living"),
    ("expense", "Household", "50.00", "monthly", "Living"),
    ("expense", "Personal Care", "50.00", "monthly", "Living"),
    ("expense", "Health", "0.00", "monthly", "Living"),
    ("expense", "Clothing", "50.00", "monthly", "Living"),
    ("expense", "Baby", "200.00", "monthly", "Living"),
    # -- Lifestyle --
    ("expense", "Subscriptions", "50.00", "monthly", "Lifestyle"),
    ("expense", "Dining Out", "100.00", "monthly", "Lifestyle"),
    ("expense", "Hobbies", "50.00", "monthly", "Lifestyle"),
    ("expense", "Fitness", "36.00", "monthly", "Lifestyle"),
    ("expense", "Travel", "50.00", "monthly", "Lifestyle"),
    ("expense", "Gifts", "30.00", "monthly", "Lifestyle"),
    # -- Sinking Funds --
    ("saving", "Emergency Fund", "200.00", "monthly", "Sinking Funds"),
    ("saving", "Car Maintenance", "50.00", "monthly", "Sinking Funds"),
    ("saving", "Renewals", "30.00", "monthly", "Sinking Funds"),
    ("saving", "Holiday Fund", "100.00", "monthly", "Sinking Funds"),
    ("saving", "Christmas", "50.00", "monthly", "Sinking Funds"),
]


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def upsert_baseline_scenario(connection: sqlite3.Connection) -> int:
    connection.execute(
        """
        INSERT INTO scenario (name, description)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET description = excluded.description
        """,
        (
            BASELINE_SCENARIO_NAME,
            "Default local planning scenario seeded from PLAN.md decisions.",
        ),
    )
    scenario_id = connection.execute(
        "SELECT id FROM scenario WHERE name = ?",
        (BASELINE_SCENARIO_NAME,),
    ).fetchone()["id"]

    assumptions = baseline_assumptions()
    connection.executemany(
        """
        INSERT INTO assumption (scenario_id, namespace, key, value, value_type, unit, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scenario_id, namespace, key) DO NOTHING
        """,
        [
            (scenario_id, namespace, key, value, value_type, unit, "plan_decision")
            for namespace, key, value, value_type, unit in assumptions
        ],
    )
    seed_example_outgoing_summaries(connection, BASELINE_SCENARIO_NAME)
    seed_bills_and_income(connection, BASELINE_SCENARIO_NAME)
    seed_plan_defaults(connection, BASELINE_SCENARIO_NAME)
    connection.commit()
    return int(scenario_id)


def baseline_assumptions() -> list[tuple[str, str, str, str, str]]:
    housing = DEFAULTS.housing
    income = DEFAULTS.income
    nursery = DEFAULTS.nursery
    categorisation = DEFAULTS.categorisation
    app = DEFAULTS
    return [
        ("housing", "flat_mortgage_balance", decimal_text(housing.flat_mortgage_balance), "money", "GBP"),
        ("housing", "flat_sale_price_low", decimal_text(housing.flat_sale_price_low), "money", "GBP"),
        ("housing", "flat_sale_price_high", decimal_text(housing.flat_sale_price_high), "money", "GBP"),
        ("housing", "estate_agent_fee_rate", decimal_text(housing.estate_agent_fee_rate), "percent", "ratio"),
        ("housing", "solicitor_fee", decimal_text(housing.solicitor_fee), "money", "GBP"),
        ("housing", "current_rent_income", decimal_text(housing.current_rent_income), "money", "GBP/month"),
        ("housing", "current_mortgage_payment", decimal_text(housing.current_mortgage_payment), "money", "GBP/month"),
        ("housing", "house_price_low", decimal_text(housing.house_price_low), "money", "GBP"),
        ("housing", "house_price_high", decimal_text(housing.house_price_high), "money", "GBP"),
        ("housing", "default_deposit_rate", decimal_text(housing.default_deposit_rate), "percent", "ratio"),
        ("housing", "default_mortgage_rate", decimal_text(housing.default_mortgage_rate), "percent", "ratio"),
        ("housing", "default_combined_gross_income", decimal_text(housing.default_combined_gross_income), "money", "GBP/year"),
        ("housing", "mortgage_term_years", str(housing.mortgage_term_years), "integer", "years"),
        ("housing", "affordability_income_multiple_low", decimal_text(housing.affordability_income_multiple_low), "decimal", "multiple"),
        ("housing", "affordability_income_multiple_high", decimal_text(housing.affordability_income_multiple_high), "decimal", "multiple"),
        ("income", "charly_hourly_rate", decimal_text(income.charly_hourly_rate), "money", "GBP/hour"),
        ("income", "charly_tax_code", income.charly_tax_code, "text", ""),
        ("income", "charly_personal_allowance", decimal_text(income.charly_personal_allowance), "money", "GBP/year"),
        ("income", "charly_pension_contribution_rate", decimal_text(income.charly_pension_contribution_rate), "percent", "ratio"),
        ("income", "charly_income_tax_basic_rate", decimal_text(income.charly_income_tax_basic_rate), "percent", "ratio"),
        ("income", "charly_income_tax_higher_rate", decimal_text(income.charly_income_tax_higher_rate), "percent", "ratio"),
        ("income", "charly_income_tax_additional_rate", decimal_text(income.charly_income_tax_additional_rate), "percent", "ratio"),
        ("income", "charly_basic_rate_limit", decimal_text(income.charly_basic_rate_limit), "money", "GBP/year"),
        ("income", "charly_higher_rate_threshold", decimal_text(income.charly_higher_rate_threshold), "money", "GBP/year"),
        ("income", "charly_ni_primary_threshold", decimal_text(income.charly_ni_primary_threshold), "money", "GBP/year"),
        ("income", "charly_ni_upper_earnings_limit", decimal_text(income.charly_ni_upper_earnings_limit), "money", "GBP/year"),
        ("income", "charly_ni_main_rate", decimal_text(income.charly_ni_main_rate), "percent", "ratio"),
        ("income", "charly_ni_upper_rate", decimal_text(income.charly_ni_upper_rate), "percent", "ratio"),
        ("income", "charly_student_loan_threshold", decimal_text(income.charly_student_loan_threshold), "money", "GBP/year"),
        ("income", "charly_student_loan_rate", decimal_text(income.charly_student_loan_rate), "percent", "ratio"),
        ("income", "charly_weekly_hours", decimal_text(income.charly_weekly_hours), "decimal", "hours/week"),
        ("income", "charly_work_hours_part_time", decimal_text(income.charly_work_hours_part_time), "decimal", "hours/week"),
        ("income", "charly_work_hours_full_time", decimal_text(income.charly_work_hours_full_time), "decimal", "hours/week"),
        ("income", "charly_work_hours_flexible", decimal_text(income.charly_work_hours_flexible), "decimal", "hours/week"),
        ("nursery", "enabled", str(nursery.enabled).lower(), "boolean", ""),
        ("nursery", "daily_cost", decimal_text(nursery.daily_cost), "money", "GBP/day"),
        ("nursery", "days_per_week", decimal_text(nursery.days_per_week), "decimal", "days"),
        ("nursery", "weekly_funded_hours", decimal_text(nursery.weekly_funded_hours), "decimal", "hours/week"),
        ("nursery", "hourly_cost", decimal_text(nursery.hourly_cost), "money", "GBP/hour"),
        ("nursery", "hours_per_day", decimal_text(nursery.hours_per_day), "decimal", "hours"),
        ("income", "alex_baseline_year", str(income.alex_baseline_year), "integer", "year"),
        ("income", "alex_base_salary_annual", decimal_text(income.alex_base_salary_annual), "money", "GBP/year"),
        ("income", "alex_select_points", decimal_text(income.alex_select_points), "decimal", "points/year"),
        ("income", "alex_select_point_value", decimal_text(income.alex_select_point_value), "money", "GBP/point"),
        ("income", "alex_pension_contribution_rate", decimal_text(income.alex_pension_contribution_rate), "percent", "ratio"),
        ("income", "alex_tax_code", income.alex_tax_code, "text", ""),
        ("income", "alex_personal_allowance", decimal_text(income.alex_personal_allowance), "money", "GBP/year"),
        ("income", "alex_income_tax_basic_rate", decimal_text(income.alex_income_tax_basic_rate), "percent", "ratio"),
        ("income", "alex_income_tax_higher_rate", decimal_text(income.alex_income_tax_higher_rate), "percent", "ratio"),
        ("income", "alex_income_tax_additional_rate", decimal_text(income.alex_income_tax_additional_rate), "percent", "ratio"),
        ("income", "alex_basic_rate_limit", decimal_text(income.alex_basic_rate_limit), "money", "GBP/year"),
        ("income", "alex_higher_rate_threshold", decimal_text(income.alex_higher_rate_threshold), "money", "GBP/year"),
        ("income", "alex_ni_primary_threshold", decimal_text(income.alex_ni_primary_threshold), "money", "GBP/year"),
        ("income", "alex_ni_upper_earnings_limit", decimal_text(income.alex_ni_upper_earnings_limit), "money", "GBP/year"),
        ("income", "alex_ni_main_rate", decimal_text(income.alex_ni_main_rate), "percent", "ratio"),
        ("income", "alex_ni_upper_rate", decimal_text(income.alex_ni_upper_rate), "percent", "ratio"),
        ("income", "alex_student_loan_threshold", decimal_text(income.alex_student_loan_threshold), "money", "GBP/year"),
        ("income", "alex_student_loan_rate", decimal_text(income.alex_student_loan_rate), "percent", "ratio"),
        ("income", "alex_stock_gross_annual", decimal_text(income.alex_stock_gross_annual), "money", "GBP/year"),
        ("income", "alex_stock_net_annual", decimal_text(income.alex_stock_net_annual), "money", "GBP/year"),
        ("income", "alex_include_stock_in_static_income", str(income.alex_include_stock_in_static_income).lower(), "boolean", ""),
        ("categorisation", "projects_scope", categorisation.projects_scope, "text", ""),
        ("categorisation", "subscriptions_scope", categorisation.subscriptions_scope, "text", ""),
        ("categorisation", "faster_payments_scope", categorisation.faster_payments_scope, "text", ""),
        ("categorisation", "monzo_pots_scope", categorisation.monzo_pots_scope, "text", ""),
        ("categorisation", "true_savings_count_as_outgoing", str(categorisation.true_savings_count_as_outgoing).lower(), "boolean", ""),
        ("app", "mortgage_rate_options", ",".join(decimal_text(value) for value in app.mortgage_rate_options), "list", "ratio"),
        ("app", "deposit_rate_options", ",".join(decimal_text(value) for value in app.deposit_rate_options), "list", "ratio"),
    ]


def parse_money(value: str) -> Decimal:
    cleaned = value.strip().replace("£", "").replace(",", "")
    return abs(Decimal(cleaned))


def parse_example_outgoing(path: Path = EXAMPLE_OUTGOING_PATH) -> list[tuple[str, Decimal, int]]:
    rows: list[tuple[str, Decimal, int]] = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        parts = [part for part in line.split("\t") if part]
        if len(parts) != 4 or parts[1] == "category":
            continue
        category = parts[1].strip()
        if category == "Income":
            continue
        rows.append((category, parse_money(parts[2]), int(parts[3])))
    return rows


def seed_bills_and_income(connection: sqlite3.Connection, scenario_name: str) -> None:
    scenario_id = get_scenario_id(connection, scenario_name)
    already_seeded = connection.execute(
        "SELECT 1 FROM manual_summary WHERE scenario_id = ? AND notes LIKE ? LIMIT 1",
        (scenario_id, f"{SEEDED_BILLS_NOTE_PREFIX}%"),
    ).fetchone()
    if already_seeded:
        return
    connection.executemany(
        """
        INSERT INTO manual_summary (scenario_id, scope, category, amount, frequency, notes, group_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (scenario_id, scope, category, amount, frequency, f"{SEEDED_BILLS_NOTE_PREFIX}; 2024 value - update to current", group_name)
            for scope, category, amount, frequency, group_name in BILLS_AND_INCOME_SEED
        ],
    )


def seed_plan_defaults(connection: sqlite3.Connection, scenario_name: str) -> None:
    """Seed the structured budget plan categories used by the /plan page."""
    scenario_id = get_scenario_id(connection, scenario_name)
    already_seeded = connection.execute(
        "SELECT 1 FROM manual_summary WHERE scenario_id = ? AND notes LIKE ? LIMIT 1",
        (scenario_id, f"{SEEDED_PLAN_NOTE_PREFIX}%"),
    ).fetchone()
    if already_seeded:
        return
    connection.executemany(
        """
        INSERT INTO manual_summary (scenario_id, scope, category, amount, frequency, notes, group_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (scenario_id, scope, category, amount, frequency, f"{SEEDED_PLAN_NOTE_PREFIX}; default value - update via Plan page", group_name)
            for scope, category, amount, frequency, group_name in PLAN_SEED
        ],
    )


def seed_example_outgoing_summaries(connection: sqlite3.Connection, scenario_name: str) -> None:
    scenario_id = get_scenario_id(connection, scenario_name)
    already_seeded = connection.execute(
        "SELECT 1 FROM manual_summary WHERE scenario_id = ? AND notes LIKE ? LIMIT 1",
        (scenario_id, f"{SEEDED_EXPENSE_NOTE_PREFIX}%"),
    ).fetchone()
    if already_seeded:
        return
    rows = parse_example_outgoing()
    connection.executemany(
        """
        INSERT INTO manual_summary (scenario_id, scope, category, amount, frequency, notes, group_name)
        VALUES (?, 'expense', ?, ?, 'monthly', ?, ?)
        """,
        [
            (scenario_id, category, decimal_text(amount), f"{SEEDED_EXPENSE_NOTE_PREFIX}; count={count}", CATEGORY_GROUP_MAP.get(category, "Household"))
            for category, amount, count in rows
        ],
    )
