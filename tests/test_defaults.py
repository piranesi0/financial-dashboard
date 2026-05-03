from decimal import Decimal
import unittest

from financials.defaults import DEFAULTS


class DefaultsTest(unittest.TestCase):
    def test_housing_defaults_match_plan_decisions(self) -> None:
        self.assertEqual(DEFAULTS.housing.flat_mortgage_balance, Decimal("259000"))
        self.assertEqual(DEFAULTS.housing.estate_agent_fee_rate, Decimal("0.0125"))
        self.assertEqual(DEFAULTS.housing.solicitor_fee, Decimal("3500"))
        self.assertEqual(DEFAULTS.housing.default_mortgage_rate, Decimal("0.045"))
        self.assertEqual(DEFAULTS.housing.default_combined_gross_income, Decimal("0"))
        self.assertEqual(DEFAULTS.housing.mortgage_term_years, 25)

    def test_income_defaults_match_plan_decisions(self) -> None:
        self.assertEqual(DEFAULTS.income.charly_hourly_rate, Decimal("21.90"))
        self.assertEqual(DEFAULTS.income.charly_tax_code, "1257L")
        self.assertEqual(DEFAULTS.income.alex_baseline_year, 2026)

    def test_categorisation_defaults_match_plan_decisions(self) -> None:
        self.assertEqual(DEFAULTS.categorisation.projects_scope, "personal")
        self.assertEqual(DEFAULTS.categorisation.subscriptions_scope, "personal")
        self.assertEqual(DEFAULTS.categorisation.faster_payments_scope, "internal_transfer")
        self.assertFalse(DEFAULTS.categorisation.true_savings_count_as_outgoing)


if __name__ == "__main__":
    unittest.main()
