from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

MONEY_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class FlatSaleInput:
    sale_price: Decimal
    outstanding_mortgage: Decimal
    estate_agent_fee_rate: Decimal
    solicitor_fee: Decimal
    early_repayment_charge: Decimal = Decimal("0")
    tax_cost: Decimal = Decimal("0")
    other_costs: Decimal = Decimal("0")


@dataclass(frozen=True)
class FlatSaleResult:
    sale_price: Decimal
    outstanding_mortgage: Decimal
    estate_agent_fee: Decimal
    solicitor_fee: Decimal
    early_repayment_charge: Decimal
    tax_cost: Decimal
    other_costs: Decimal
    total_costs: Decimal
    net_proceeds: Decimal


@dataclass(frozen=True)
class MortgageInput:
    purchase_price: Decimal
    deposit_rate: Decimal
    annual_interest_rate: Decimal
    term_years: int


@dataclass(frozen=True)
class MortgageResult:
    purchase_price: Decimal
    deposit: Decimal
    principal: Decimal
    annual_interest_rate: Decimal
    term_years: int
    monthly_payment: Decimal
    annual_payment: Decimal


@dataclass(frozen=True)
class AffordabilityResult:
    combined_gross_income: Decimal
    low_multiple: Decimal
    high_multiple: Decimal
    low_max_borrowing: Decimal
    high_max_borrowing: Decimal
    deposit: Decimal
    low_max_purchase_price: Decimal
    high_max_purchase_price: Decimal


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def calculate_flat_sale(inputs: FlatSaleInput) -> FlatSaleResult:
    estate_agent_fee = money(inputs.sale_price * inputs.estate_agent_fee_rate)
    total_costs = money(
        inputs.outstanding_mortgage
        + estate_agent_fee
        + inputs.solicitor_fee
        + inputs.early_repayment_charge
        + inputs.tax_cost
        + inputs.other_costs
    )
    return FlatSaleResult(
        sale_price=money(inputs.sale_price),
        outstanding_mortgage=money(inputs.outstanding_mortgage),
        estate_agent_fee=estate_agent_fee,
        solicitor_fee=money(inputs.solicitor_fee),
        early_repayment_charge=money(inputs.early_repayment_charge),
        tax_cost=money(inputs.tax_cost),
        other_costs=money(inputs.other_costs),
        total_costs=total_costs,
        net_proceeds=money(inputs.sale_price - total_costs),
    )


def calculate_repayment_mortgage(inputs: MortgageInput) -> MortgageResult:
    deposit = money(inputs.purchase_price * inputs.deposit_rate)
    principal = money(inputs.purchase_price - deposit)
    months = inputs.term_years * 12
    monthly_rate = inputs.annual_interest_rate / Decimal("12")

    if monthly_rate == 0:
        monthly_payment = money(principal / Decimal(months))
    else:
        rate = float(monthly_rate)
        principal_float = float(principal)
        payment = principal_float * (rate * (1 + rate) ** months) / ((1 + rate) ** months - 1)
        monthly_payment = money(Decimal(str(payment)))

    return MortgageResult(
        purchase_price=money(inputs.purchase_price),
        deposit=deposit,
        principal=principal,
        annual_interest_rate=inputs.annual_interest_rate,
        term_years=inputs.term_years,
        monthly_payment=monthly_payment,
        annual_payment=money(monthly_payment * Decimal("12")),
    )


def calculate_affordability(
    combined_gross_income: Decimal,
    deposit: Decimal,
    low_multiple: Decimal = Decimal("4.0"),
    high_multiple: Decimal = Decimal("4.5"),
) -> AffordabilityResult:
    low_max_borrowing = money(combined_gross_income * low_multiple)
    high_max_borrowing = money(combined_gross_income * high_multiple)
    return AffordabilityResult(
        combined_gross_income=money(combined_gross_income),
        low_multiple=low_multiple,
        high_multiple=high_multiple,
        low_max_borrowing=low_max_borrowing,
        high_max_borrowing=high_max_borrowing,
        deposit=money(deposit),
        low_max_purchase_price=money(low_max_borrowing + deposit),
        high_max_purchase_price=money(high_max_borrowing + deposit),
    )
