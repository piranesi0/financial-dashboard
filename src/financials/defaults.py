from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class HousingDefaults:
    flat_mortgage_balance: Decimal = Decimal("259000")
    flat_sale_price_low: Decimal = Decimal("290000")
    flat_sale_price_high: Decimal = Decimal("320000")
    estate_agent_fee_rate: Decimal = Decimal("0.0125")
    solicitor_fee: Decimal = Decimal("3500")
    current_rent_income: Decimal = Decimal("1144")
    current_mortgage_payment: Decimal = Decimal("1124.10")
    house_price_low: Decimal = Decimal("300000")
    house_price_high: Decimal = Decimal("450000")
    default_deposit_rate: Decimal = Decimal("0.10")
    default_mortgage_rate: Decimal = Decimal("0.045")
    default_combined_gross_income: Decimal = Decimal("0")
    mortgage_term_years: int = 25
    affordability_income_multiple_low: Decimal = Decimal("4.0")
    affordability_income_multiple_high: Decimal = Decimal("4.5")


@dataclass(frozen=True)
class NurseryDefaults:
    daily_cost: Decimal = Decimal("70.00")
    days_per_week: Decimal = Decimal("3")
    weekly_funded_hours: Decimal = Decimal("15")
    hourly_cost: Decimal = Decimal("8.50")
    hours_per_day: Decimal = Decimal("9")


@dataclass(frozen=True)
class IncomeDefaults:
    charly_hourly_rate: Decimal = Decimal("21.90")
    charly_tax_code: str = "1257L"
    charly_personal_allowance: Decimal = Decimal("12570")
    charly_pension_contribution_rate: Decimal = Decimal("0.05")
    charly_income_tax_basic_rate: Decimal = Decimal("0.20")
    charly_income_tax_higher_rate: Decimal = Decimal("0.40")
    charly_income_tax_additional_rate: Decimal = Decimal("0.45")
    charly_basic_rate_limit: Decimal = Decimal("37700")
    charly_higher_rate_threshold: Decimal = Decimal("125140")
    charly_ni_primary_threshold: Decimal = Decimal("12570")
    charly_ni_upper_earnings_limit: Decimal = Decimal("50270")
    charly_ni_main_rate: Decimal = Decimal("0.08")
    charly_ni_upper_rate: Decimal = Decimal("0.02")
    charly_student_loan_threshold: Decimal = Decimal("27295")
    charly_student_loan_rate: Decimal = Decimal("0.09")
    charly_weekly_hours: Decimal = Decimal("0")
    charly_work_hours_part_time: Decimal = Decimal("20")
    charly_work_hours_full_time: Decimal = Decimal("37.5")
    charly_work_hours_flexible: Decimal = Decimal("25")
    alex_baseline_year: int = 2026
    alex_base_salary_annual: Decimal = Decimal("50495.24")
    alex_select_points: Decimal = Decimal("8622.3544")
    alex_select_point_value: Decimal = Decimal("1")
    alex_pension_contribution_rate: Decimal = Decimal("0.092071")
    alex_tax_code: str = "1257L"
    alex_personal_allowance: Decimal = Decimal("12570")
    alex_income_tax_basic_rate: Decimal = Decimal("0.20")
    alex_income_tax_higher_rate: Decimal = Decimal("0.40")
    alex_income_tax_additional_rate: Decimal = Decimal("0.45")
    alex_basic_rate_limit: Decimal = Decimal("37700")
    alex_higher_rate_threshold: Decimal = Decimal("125140")
    alex_ni_primary_threshold: Decimal = Decimal("12570")
    alex_ni_upper_earnings_limit: Decimal = Decimal("50270")
    alex_ni_main_rate: Decimal = Decimal("0.08")
    alex_ni_upper_rate: Decimal = Decimal("0.02")
    alex_stock_gross_annual: Decimal = Decimal("14801.60748")
    alex_stock_net_annual: Decimal = Decimal("6660.723365")
    alex_include_stock_in_static_income: bool = False


@dataclass(frozen=True)
class CategorisationDefaults:
    projects_scope: str = "personal"
    subscriptions_scope: str = "personal"
    faster_payments_scope: str = "internal_transfer"
    monzo_pots_scope: str = "budgeting"
    true_savings_count_as_outgoing: bool = False


@dataclass(frozen=True)
class AppDefaults:
    housing: HousingDefaults = HousingDefaults()
    income: IncomeDefaults = IncomeDefaults()
    nursery: NurseryDefaults = NurseryDefaults()
    categorisation: CategorisationDefaults = CategorisationDefaults()
    mortgage_rate_options: tuple[Decimal, ...] = (
        Decimal("0.035"),
        Decimal("0.04"),
        Decimal("0.045"),
        Decimal("0.05"),
    )
    deposit_rate_options: tuple[Decimal, ...] = (
        Decimal("0.05"),
        Decimal("0.10"),
        Decimal("0.15"),
    )


DEFAULTS = AppDefaults()
