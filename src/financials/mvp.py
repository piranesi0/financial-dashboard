from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from financials.calculators.charly import CharlyIncomeInput, CharlyIncomeResult, calculate_charly_income
from financials.calculators.housing import (
    AffordabilityResult,
    FlatSaleInput,
    FlatSaleResult,
    MortgageInput,
    MortgageResult,
    calculate_affordability,
    calculate_flat_sale,
    calculate_repayment_mortgage,
)
from financials.calculators.income import StaticIncomeInput, StaticIncomeResult, calculate_static_income
from financials.calculators.nursery import NurseryInput, NurseryResult, calculate_nursery
from financials.outputs import persist_calculator_outputs
from financials.scenario import assumption_bool, assumption_decimal, assumption_int, get_assumptions
from financials.summaries import HouseholdSummary, calculate_household_summary, list_manual_summaries


def _charly_input_from_assumptions(assumptions: dict, weekly_hours: Decimal) -> CharlyIncomeInput:
    return CharlyIncomeInput(
        hourly_rate=assumption_decimal(assumptions, "income", "charly_hourly_rate"),
        weekly_hours=weekly_hours,
        pension_contribution_rate=assumption_decimal(assumptions, "income", "charly_pension_contribution_rate"),
        personal_allowance=assumption_decimal(assumptions, "income", "charly_personal_allowance"),
        basic_rate_limit=assumption_decimal(assumptions, "income", "charly_basic_rate_limit"),
        higher_rate_threshold=assumption_decimal(assumptions, "income", "charly_higher_rate_threshold"),
        income_tax_basic_rate=assumption_decimal(assumptions, "income", "charly_income_tax_basic_rate"),
        income_tax_higher_rate=assumption_decimal(assumptions, "income", "charly_income_tax_higher_rate"),
        income_tax_additional_rate=assumption_decimal(assumptions, "income", "charly_income_tax_additional_rate"),
        ni_primary_threshold=assumption_decimal(assumptions, "income", "charly_ni_primary_threshold"),
        ni_upper_earnings_limit=assumption_decimal(assumptions, "income", "charly_ni_upper_earnings_limit"),
        ni_main_rate=assumption_decimal(assumptions, "income", "charly_ni_main_rate"),
        ni_upper_rate=assumption_decimal(assumptions, "income", "charly_ni_upper_rate"),
        student_loan_threshold=assumption_decimal(assumptions, "income", "charly_student_loan_threshold"),
        student_loan_rate=assumption_decimal(assumptions, "income", "charly_student_loan_rate"),
    )


def calculate_charly_income_for_scenario(
    connection: sqlite3.Connection,
    scenario_name: str,
    weekly_hours: Decimal | None = None,
) -> CharlyIncomeResult:
    assumptions = get_assumptions(connection, scenario_name)
    hours = weekly_hours if weekly_hours is not None else assumption_decimal(assumptions, "income", "charly_weekly_hours")
    return calculate_charly_income(_charly_input_from_assumptions(assumptions, hours))


def calculate_charly_all_scenarios(
    connection: sqlite3.Connection,
    scenario_name: str,
) -> dict[str, CharlyIncomeResult]:
    assumptions = get_assumptions(connection, scenario_name)
    scenarios = {
        "none": Decimal("0"),
        "part_time": assumption_decimal(assumptions, "income", "charly_work_hours_part_time"),
        "full_time": assumption_decimal(assumptions, "income", "charly_work_hours_full_time"),
        "flexible": assumption_decimal(assumptions, "income", "charly_work_hours_flexible"),
    }
    return {
        label: calculate_charly_income(_charly_input_from_assumptions(assumptions, hours))
        for label, hours in scenarios.items()
    }


def calculate_nursery_for_scenario(
    connection: sqlite3.Connection,
    scenario_name: str,
) -> NurseryResult:
    assumptions = get_assumptions(connection, scenario_name)
    enabled = assumption_bool(assumptions, "nursery", "enabled", default=True)
    if not enabled:
        zero = Decimal("0")
        return NurseryResult(
            days_per_week=assumption_decimal(assumptions, "nursery", "days_per_week"),
            weekly_gross_cost=zero,
            monthly_gross_cost=zero,
            weekly_funded_hours_applied=zero,
            monthly_funded_saving=zero,
            monthly_net_cost=zero,
            annual_net_cost=zero,
        )
    return calculate_nursery(
        NurseryInput(
            days_per_week=assumption_decimal(assumptions, "nursery", "days_per_week"),
            daily_cost=assumption_decimal(assumptions, "nursery", "daily_cost"),
            weekly_funded_hours=assumption_decimal(assumptions, "nursery", "weekly_funded_hours"),
            hourly_cost=assumption_decimal(assumptions, "nursery", "hourly_cost"),
            hours_per_day=assumption_decimal(assumptions, "nursery", "hours_per_day"),
        )
    )


@dataclass(frozen=True)
class HousingScenarioSummary:
    flat_sale: FlatSaleResult
    mortgage: MortgageResult
    affordability: AffordabilityResult


@dataclass(frozen=True)
class MvpScenarioSummary:
    alex_income: StaticIncomeResult
    housing: HousingScenarioSummary
    household: HouseholdSummary


def calculate_alex_static_income_for_scenario(
    connection: sqlite3.Connection,
    scenario_name: str,
    persist: bool = False,
) -> StaticIncomeResult:
    assumptions = get_assumptions(connection, scenario_name)
    result = calculate_static_income(
        StaticIncomeInput(
            base_salary_annual=assumption_decimal(assumptions, "income", "alex_base_salary_annual"),
            select_points=assumption_decimal(assumptions, "income", "alex_select_points"),
            select_point_value=assumption_decimal(assumptions, "income", "alex_select_point_value"),
            pension_contribution_rate=assumption_decimal(assumptions, "income", "alex_pension_contribution_rate"),
            personal_allowance=assumption_decimal(assumptions, "income", "alex_personal_allowance"),
            basic_rate_limit=assumption_decimal(assumptions, "income", "alex_basic_rate_limit"),
            higher_rate_threshold=assumption_decimal(assumptions, "income", "alex_higher_rate_threshold"),
            income_tax_basic_rate=assumption_decimal(assumptions, "income", "alex_income_tax_basic_rate"),
            income_tax_higher_rate=assumption_decimal(assumptions, "income", "alex_income_tax_higher_rate"),
            income_tax_additional_rate=assumption_decimal(assumptions, "income", "alex_income_tax_additional_rate"),
            ni_primary_threshold=assumption_decimal(assumptions, "income", "alex_ni_primary_threshold"),
            ni_upper_earnings_limit=assumption_decimal(assumptions, "income", "alex_ni_upper_earnings_limit"),
            ni_main_rate=assumption_decimal(assumptions, "income", "alex_ni_main_rate"),
            ni_upper_rate=assumption_decimal(assumptions, "income", "alex_ni_upper_rate"),
            stock_net_annual=assumption_decimal(assumptions, "income", "alex_stock_net_annual"),
            include_stock_in_static_income=assumption_bool(assumptions, "income", "alex_include_stock_in_static_income"),
        )
    )
    if persist:
        persist_calculator_outputs(
            connection,
            scenario_name,
            "alex_static_income",
            {
                "gross_employment_income_annual": (result.gross_employment_income_annual, "GBP/year"),
                "pension_contribution_annual": (result.pension_contribution_annual, "GBP/year"),
                "income_tax_annual": (result.income_tax_annual, "GBP/year"),
                "national_insurance_annual": (result.national_insurance_annual, "GBP/year"),
                "net_income_annual": (result.net_income_annual, "GBP/year"),
                "net_income_monthly": (result.net_income_monthly, "GBP/month"),
            },
        )
    return result


def calculate_housing_for_scenario(
    connection: sqlite3.Connection,
    scenario_name: str,
    sale_price: Decimal | None = None,
    house_price: Decimal | None = None,
    deposit_rate: Decimal | None = None,
    mortgage_rate: Decimal | None = None,
    combined_gross_income: Decimal | None = None,
    persist: bool = False,
) -> HousingScenarioSummary:
    assumptions = get_assumptions(connection, scenario_name)
    resolved_sale_price = sale_price or assumption_decimal(assumptions, "housing", "flat_sale_price_low")
    resolved_house_price = house_price or assumption_decimal(assumptions, "housing", "house_price_low")
    resolved_deposit_rate = deposit_rate or assumption_decimal(assumptions, "housing", "default_deposit_rate")
    resolved_mortgage_rate = mortgage_rate or assumption_decimal(assumptions, "housing", "default_mortgage_rate")
    resolved_combined_gross_income = combined_gross_income or assumption_decimal(
        assumptions,
        "housing",
        "default_combined_gross_income",
    )

    flat_sale = calculate_flat_sale(
        FlatSaleInput(
            sale_price=resolved_sale_price,
            outstanding_mortgage=assumption_decimal(assumptions, "housing", "flat_mortgage_balance"),
            estate_agent_fee_rate=assumption_decimal(assumptions, "housing", "estate_agent_fee_rate"),
            solicitor_fee=assumption_decimal(assumptions, "housing", "solicitor_fee"),
        )
    )
    mortgage = calculate_repayment_mortgage(
        MortgageInput(
            purchase_price=resolved_house_price,
            deposit_rate=resolved_deposit_rate,
            annual_interest_rate=resolved_mortgage_rate,
            term_years=assumption_int(assumptions, "housing", "mortgage_term_years"),
        )
    )
    affordability = calculate_affordability(
        combined_gross_income=resolved_combined_gross_income,
        deposit=mortgage.deposit,
        low_multiple=assumption_decimal(assumptions, "housing", "affordability_income_multiple_low"),
        high_multiple=assumption_decimal(assumptions, "housing", "affordability_income_multiple_high"),
    )

    if persist:
        persist_calculator_outputs(
            connection,
            scenario_name,
            "housing",
            {
                "flat_sale_net_proceeds": (flat_sale.net_proceeds, "GBP"),
                "flat_sale_total_costs": (flat_sale.total_costs, "GBP"),
                "mortgage_monthly_payment": (mortgage.monthly_payment, "GBP/month"),
                "mortgage_principal": (mortgage.principal, "GBP"),
                "affordability_low_max_purchase_price": (affordability.low_max_purchase_price, "GBP"),
                "affordability_high_max_purchase_price": (affordability.high_max_purchase_price, "GBP"),
            },
        )

    return HousingScenarioSummary(
        flat_sale=flat_sale,
        mortgage=mortgage,
        affordability=affordability,
    )


def calculate_mvp_summary(
    connection: sqlite3.Connection,
    scenario_name: str,
    sale_price: Decimal | None = None,
    house_price: Decimal | None = None,
    deposit_rate: Decimal | None = None,
    mortgage_rate: Decimal | None = None,
    combined_gross_income: Decimal | None = None,
    persist: bool = False,
) -> MvpScenarioSummary:
    alex_income = calculate_alex_static_income_for_scenario(connection, scenario_name, persist=persist)
    housing = calculate_housing_for_scenario(
        connection=connection,
        scenario_name=scenario_name,
        sale_price=sale_price,
        house_price=house_price,
        deposit_rate=deposit_rate,
        mortgage_rate=mortgage_rate,
        combined_gross_income=combined_gross_income,
        persist=persist,
    )
    household = calculate_household_summary(list_manual_summaries(connection, scenario_name))

    if persist:
        persist_calculator_outputs(
            connection,
            scenario_name,
            "household_summary",
            {
                "monthly_income": (household.monthly_income, "GBP/month"),
                "monthly_expenses": (household.monthly_expenses, "GBP/month"),
                "monthly_savings": (household.monthly_savings, "GBP/month"),
                "monthly_net": (household.monthly_net, "GBP/month"),
            },
        )

    return MvpScenarioSummary(alex_income=alex_income, housing=housing, household=household)
