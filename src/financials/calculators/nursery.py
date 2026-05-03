from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from financials.calculators.housing import money

TERM_WEEKS_PER_YEAR = Decimal("38")
WEEKS_PER_YEAR = Decimal("52")
MONTHS_PER_YEAR = Decimal("12")


@dataclass(frozen=True)
class NurseryInput:
    days_per_week: Decimal
    daily_cost: Decimal
    weekly_funded_hours: Decimal
    hourly_cost: Decimal
    hours_per_day: Decimal = Decimal("9")


@dataclass(frozen=True)
class NurseryResult:
    days_per_week: Decimal
    weekly_gross_cost: Decimal
    monthly_gross_cost: Decimal
    weekly_funded_hours_applied: Decimal
    monthly_funded_saving: Decimal
    monthly_net_cost: Decimal
    annual_net_cost: Decimal


def calculate_nursery(inputs: NurseryInput) -> NurseryResult:
    weekly_gross = money(inputs.days_per_week * inputs.daily_cost)
    monthly_gross = money(weekly_gross * WEEKS_PER_YEAR / MONTHS_PER_YEAR)

    # Funded hours apply only during term time (~38 weeks/year in England).
    # Applied hours can't exceed actual nursery hours per week.
    nursery_hours_per_week = inputs.days_per_week * inputs.hours_per_day
    funded_hours_applied = min(inputs.weekly_funded_hours, nursery_hours_per_week)
    monthly_funded_saving = money(
        funded_hours_applied * inputs.hourly_cost * TERM_WEEKS_PER_YEAR / MONTHS_PER_YEAR
    )

    monthly_net = money(monthly_gross - monthly_funded_saving)

    return NurseryResult(
        days_per_week=inputs.days_per_week,
        weekly_gross_cost=weekly_gross,
        monthly_gross_cost=monthly_gross,
        weekly_funded_hours_applied=funded_hours_applied,
        monthly_funded_saving=monthly_funded_saving,
        monthly_net_cost=monthly_net,
        annual_net_cost=money(monthly_net * MONTHS_PER_YEAR),
    )
