from decimal import Decimal
import unittest

from financials.calculators.housing import (
    FlatSaleInput,
    MortgageInput,
    calculate_affordability,
    calculate_flat_sale,
    calculate_repayment_mortgage,
)


class HousingCalculatorTest(unittest.TestCase):
    def test_flat_sale_net_proceeds(self) -> None:
        result = calculate_flat_sale(
            FlatSaleInput(
                sale_price=Decimal("300000"),
                outstanding_mortgage=Decimal("259000"),
                estate_agent_fee_rate=Decimal("0.0125"),
                solicitor_fee=Decimal("3500"),
            )
        )

        self.assertEqual(result.estate_agent_fee, Decimal("3750.00"))
        self.assertEqual(result.total_costs, Decimal("266250.00"))
        self.assertEqual(result.net_proceeds, Decimal("33750.00"))

    def test_repayment_mortgage_monthly_payment(self) -> None:
        result = calculate_repayment_mortgage(
            MortgageInput(
                purchase_price=Decimal("350000"),
                deposit_rate=Decimal("0.10"),
                annual_interest_rate=Decimal("0.045"),
                term_years=25,
            )
        )

        self.assertEqual(result.deposit, Decimal("35000.00"))
        self.assertEqual(result.principal, Decimal("315000.00"))
        self.assertEqual(result.monthly_payment, Decimal("1750.87"))

    def test_affordability(self) -> None:
        result = calculate_affordability(
            combined_gross_income=Decimal("90000"),
            deposit=Decimal("35000"),
            low_multiple=Decimal("4.0"),
            high_multiple=Decimal("4.5"),
        )

        self.assertEqual(result.low_max_borrowing, Decimal("360000.00"))
        self.assertEqual(result.high_max_borrowing, Decimal("405000.00"))
        self.assertEqual(result.low_max_purchase_price, Decimal("395000.00"))
        self.assertEqual(result.high_max_purchase_price, Decimal("440000.00"))


if __name__ == "__main__":
    unittest.main()
