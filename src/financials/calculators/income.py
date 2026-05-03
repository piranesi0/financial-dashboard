from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from financials.calculators.housing import money


@dataclass(frozen=True)
class StaticIncomeInput:
    base_salary_annual: Decimal
    select_points: Decimal
    select_point_value: Decimal
    pension_contribution_rate: Decimal
    personal_allowance: Decimal
    basic_rate_limit: Decimal
    higher_rate_threshold: Decimal
    income_tax_basic_rate: Decimal
    income_tax_higher_rate: Decimal
    income_tax_additional_rate: Decimal
    ni_primary_threshold: Decimal
    ni_upper_earnings_limit: Decimal
    ni_main_rate: Decimal
    ni_upper_rate: Decimal
    stock_net_annual: Decimal = Decimal("0")
    include_stock_in_static_income: bool = False


@dataclass(frozen=True)
class StaticIncomeResult:
    base_salary_annual: Decimal
    select_income_annual: Decimal
    gross_employment_income_annual: Decimal
    pension_contribution_annual: Decimal
    taxable_income_annual: Decimal
    income_tax_annual: Decimal
    national_insurance_annual: Decimal
    stock_net_annual: Decimal
    net_income_annual: Decimal
    net_income_monthly: Decimal


def tax_band_amount(value: Decimal, lower: Decimal, upper: Decimal | None) -> Decimal:
    if value <= lower:
        return Decimal("0")
    if upper is None:
        return value - lower
    return max(Decimal("0"), min(value, upper) - lower)


def calculate_static_income(inputs: StaticIncomeInput) -> StaticIncomeResult:
    select_income = money(inputs.select_points * inputs.select_point_value)
    gross_employment_income = money(inputs.base_salary_annual + select_income)
    pension_contribution = money(gross_employment_income * inputs.pension_contribution_rate)
    taxable_income = money(max(Decimal("0"), gross_employment_income - pension_contribution - inputs.personal_allowance))

    basic_taxable = min(taxable_income, inputs.basic_rate_limit)
    higher_taxable = tax_band_amount(taxable_income, inputs.basic_rate_limit, inputs.higher_rate_threshold - inputs.personal_allowance)
    additional_taxable = tax_band_amount(taxable_income, inputs.higher_rate_threshold - inputs.personal_allowance, None)
    income_tax = money(
        basic_taxable * inputs.income_tax_basic_rate
        + higher_taxable * inputs.income_tax_higher_rate
        + additional_taxable * inputs.income_tax_additional_rate
    )

    ni_main = tax_band_amount(gross_employment_income, inputs.ni_primary_threshold, inputs.ni_upper_earnings_limit)
    ni_upper = tax_band_amount(gross_employment_income, inputs.ni_upper_earnings_limit, None)
    national_insurance = money(ni_main * inputs.ni_main_rate + ni_upper * inputs.ni_upper_rate)

    stock_net = money(inputs.stock_net_annual if inputs.include_stock_in_static_income else Decimal("0"))
    net_income = money(gross_employment_income - pension_contribution - income_tax - national_insurance + stock_net)
    return StaticIncomeResult(
        base_salary_annual=money(inputs.base_salary_annual),
        select_income_annual=select_income,
        gross_employment_income_annual=gross_employment_income,
        pension_contribution_annual=pension_contribution,
        taxable_income_annual=taxable_income,
        income_tax_annual=income_tax,
        national_insurance_annual=national_insurance,
        stock_net_annual=stock_net,
        net_income_annual=net_income,
        net_income_monthly=money(net_income / Decimal("12")),
    )
