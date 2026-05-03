from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from financials.calculators.housing import money
from financials.calculators.income import tax_band_amount


@dataclass(frozen=True)
class CharlyIncomeInput:
    hourly_rate: Decimal
    weekly_hours: Decimal
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
    student_loan_threshold: Decimal
    student_loan_rate: Decimal


@dataclass(frozen=True)
class CharlyIncomeResult:
    weekly_hours: Decimal
    gross_annual: Decimal
    gross_monthly: Decimal
    pension_annual: Decimal
    taxable_income_annual: Decimal
    income_tax_annual: Decimal
    national_insurance_annual: Decimal
    student_loan_annual: Decimal
    net_annual: Decimal
    net_monthly: Decimal


def calculate_charly_income(inputs: CharlyIncomeInput) -> CharlyIncomeResult:
    gross_annual = money(inputs.hourly_rate * inputs.weekly_hours * Decimal("52"))
    pension = money(gross_annual * inputs.pension_contribution_rate)
    taxable_income = money(max(Decimal("0"), gross_annual - pension - inputs.personal_allowance))

    basic_taxable = min(taxable_income, inputs.basic_rate_limit)
    higher_taxable = tax_band_amount(
        taxable_income,
        inputs.basic_rate_limit,
        inputs.higher_rate_threshold - inputs.personal_allowance,
    )
    additional_taxable = tax_band_amount(
        taxable_income,
        inputs.higher_rate_threshold - inputs.personal_allowance,
        None,
    )
    income_tax = money(
        basic_taxable * inputs.income_tax_basic_rate
        + higher_taxable * inputs.income_tax_higher_rate
        + additional_taxable * inputs.income_tax_additional_rate
    )

    ni_main = tax_band_amount(gross_annual, inputs.ni_primary_threshold, inputs.ni_upper_earnings_limit)
    ni_upper = tax_band_amount(gross_annual, inputs.ni_upper_earnings_limit, None)
    national_insurance = money(ni_main * inputs.ni_main_rate + ni_upper * inputs.ni_upper_rate)

    student_loan = money(
        max(Decimal("0"), gross_annual - inputs.student_loan_threshold) * inputs.student_loan_rate
    )

    net_annual = money(gross_annual - pension - income_tax - national_insurance - student_loan)

    return CharlyIncomeResult(
        weekly_hours=inputs.weekly_hours,
        gross_annual=gross_annual,
        gross_monthly=money(gross_annual / Decimal("12")),
        pension_annual=pension,
        taxable_income_annual=taxable_income,
        income_tax_annual=income_tax,
        national_insurance_annual=national_insurance,
        student_loan_annual=student_loan,
        net_annual=net_annual,
        net_monthly=money(net_annual / Decimal("12")),
    )
