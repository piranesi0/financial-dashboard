from decimal import Decimal
import unittest

from financials.calculators.charly import CharlyIncomeInput, calculate_charly_income


def _base_input(weekly_hours: Decimal) -> CharlyIncomeInput:
    return CharlyIncomeInput(
        hourly_rate=Decimal("21.90"),
        weekly_hours=weekly_hours,
        pension_contribution_rate=Decimal("0.05"),
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
        student_loan_threshold=Decimal("27295"),
        student_loan_rate=Decimal("0.09"),
    )


class CharlyIncomeTest(unittest.TestCase):
    def test_not_working_zero_income(self) -> None:
        result = calculate_charly_income(_base_input(Decimal("0")))

        self.assertEqual(result.gross_annual, Decimal("0.00"))
        self.assertEqual(result.net_monthly, Decimal("0.00"))
        self.assertEqual(result.income_tax_annual, Decimal("0.00"))
        self.assertEqual(result.national_insurance_annual, Decimal("0.00"))
        self.assertEqual(result.student_loan_annual, Decimal("0.00"))

    def test_part_time_20hrs(self) -> None:
        # Gross = 21.90 × 20 × 52 = 22,776
        # Pension = 22,776 × 0.05 = 1,138.80
        # Taxable = 22,776 - 1,138.80 - 12,570 = 9,067.20
        # Tax = 9,067.20 × 0.20 = 1,813.44
        # NI = (22,776 - 12,570) × 0.08 = 816.48
        # SL = 0 (below £27,295 threshold)
        # Net = 22,776 - 1,138.80 - 1,813.44 - 816.48 = 19,007.28 → 1,583.94/mo
        result = calculate_charly_income(_base_input(Decimal("20")))

        self.assertEqual(result.gross_annual, Decimal("22776.00"))
        self.assertEqual(result.pension_annual, Decimal("1138.80"))
        self.assertEqual(result.income_tax_annual, Decimal("1813.44"))
        self.assertEqual(result.national_insurance_annual, Decimal("816.48"))
        self.assertEqual(result.student_loan_annual, Decimal("0.00"))
        self.assertEqual(result.net_annual, Decimal("19007.28"))
        self.assertEqual(result.net_monthly, Decimal("1583.94"))

    def test_full_time_375hrs(self) -> None:
        # Gross = 21.90 × 37.5 × 52 = 42,705
        # Pension = 42,705 × 0.05 = 2,135.25
        # Taxable = 42,705 - 2,135.25 - 12,570 = 27,999.75
        # Tax = 27,999.75 × 0.20 = 5,599.95
        # NI = (42,705 - 12,570) × 0.08 = 2,410.80
        # SL = (42,705 - 27,295) × 0.09 = 1,386.90
        # Net = 42,705 - 2,135.25 - 5,599.95 - 2,410.80 - 1,386.90 = 31,172.10 → 2,597.68/mo
        result = calculate_charly_income(_base_input(Decimal("37.5")))

        self.assertEqual(result.gross_annual, Decimal("42705.00"))
        self.assertEqual(result.pension_annual, Decimal("2135.25"))
        self.assertEqual(result.income_tax_annual, Decimal("5599.95"))
        self.assertEqual(result.national_insurance_annual, Decimal("2410.80"))
        self.assertEqual(result.student_loan_annual, Decimal("1386.90"))
        self.assertEqual(result.net_annual, Decimal("31172.10"))
        self.assertEqual(result.net_monthly, Decimal("2597.68"))

    def test_flexible_25hrs(self) -> None:
        # Gross = 21.90 × 25 × 52 = 28,470
        # Pension = 28,470 × 0.05 = 1,423.50
        # Taxable = 28,470 - 1,423.50 - 12,570 = 14,476.50
        # Tax = 14,476.50 × 0.20 = 2,895.30
        # NI = (28,470 - 12,570) × 0.08 = 1,272.00
        # SL = (28,470 - 27,295) × 0.09 = 105.75
        # Net = 28,470 - 1,423.50 - 2,895.30 - 1,272.00 - 105.75 = 22,773.45 → 1,897.79/mo
        result = calculate_charly_income(_base_input(Decimal("25")))

        self.assertEqual(result.gross_annual, Decimal("28470.00"))
        self.assertEqual(result.pension_annual, Decimal("1423.50"))
        self.assertEqual(result.income_tax_annual, Decimal("2895.30"))
        self.assertEqual(result.national_insurance_annual, Decimal("1272.00"))
        self.assertEqual(result.student_loan_annual, Decimal("105.75"))
        self.assertEqual(result.net_annual, Decimal("22773.45"))
        self.assertEqual(result.net_monthly, Decimal("1897.79"))

    def test_gross_monthly_is_gross_annual_divided_by_12(self) -> None:
        result = calculate_charly_income(_base_input(Decimal("30")))
        from financials.calculators.housing import money
        self.assertEqual(result.gross_monthly, money(result.gross_annual / 12))


if __name__ == "__main__":
    unittest.main()
