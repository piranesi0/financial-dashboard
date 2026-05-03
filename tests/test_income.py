from decimal import Decimal
import unittest

from financials.calculators.income import StaticIncomeInput, calculate_static_income


class StaticIncomeTest(unittest.TestCase):
    def test_calculate_static_income(self) -> None:
        result = calculate_static_income(
            StaticIncomeInput(
                base_salary_annual=Decimal("50495.24"),
                select_points=Decimal("8622.3544"),
                select_point_value=Decimal("1"),
                pension_contribution_rate=Decimal("0.092071"),
                personal_allowance=Decimal("12570"),
                basic_rate_limit=Decimal("37700"),
                higher_rate_threshold=Decimal("125140"),
                income_tax_basic_rate=Decimal("0.20"),
                income_tax_higher_rate=Decimal("0.40"),
                income_tax_additional_rate=Decimal("0.45"),
                ni_primary_threshold=Decimal("12570"),
                ni_upper_earnings_limit=Decimal("50270"),
                ni_main_rate=Decimal("0.08"),
                ni_upper_rate=Decimal("0.02"),
            )
        )

        self.assertEqual(result.select_income_annual, Decimal("8622.35"))
        self.assertEqual(result.gross_employment_income_annual, Decimal("59117.59"))
        self.assertEqual(result.pension_contribution_annual, Decimal("5443.02"))
        self.assertEqual(result.net_income_monthly, Decimal("3464.98"))


if __name__ == "__main__":
    unittest.main()
