from decimal import Decimal
import unittest

from financials.mvp import calculate_alex_static_income_for_scenario, calculate_housing_for_scenario, calculate_mvp_summary
from financials.schema import initialise_database
from financials.seeds import upsert_baseline_scenario
from financials.summaries import add_manual_summary


class MvpTest(unittest.TestCase):
    def test_calculate_alex_static_income_for_scenario(self) -> None:
        connection = initialise_database(":memory:")
        upsert_baseline_scenario(connection)

        result = calculate_alex_static_income_for_scenario(connection, "baseline", persist=True)
        outputs = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM calculator_output WHERE calculator = 'alex_static_income'").fetchall()
        }
        connection.close()

        self.assertEqual(result.gross_employment_income_annual, Decimal("59117.59"))
        self.assertEqual(result.net_income_monthly, Decimal("3226.31"))
        self.assertEqual(outputs["net_income_monthly"], "3226.31")

    def test_calculate_housing_for_scenario_uses_seeded_assumptions(self) -> None:
        connection = initialise_database(":memory:")
        upsert_baseline_scenario(connection)

        result = calculate_housing_for_scenario(
            connection,
            "baseline",
            sale_price=Decimal("300000"),
            house_price=Decimal("350000"),
            deposit_rate=Decimal("0.10"),
            mortgage_rate=Decimal("0.045"),
            combined_gross_income=Decimal("90000"),
            persist=True,
        )
        outputs = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM calculator_output WHERE calculator = 'housing'").fetchall()
        }
        connection.close()

        self.assertEqual(result.flat_sale.net_proceeds, Decimal("33750.00"))
        self.assertEqual(result.mortgage.monthly_payment, Decimal("1750.87"))
        self.assertEqual(outputs["flat_sale_net_proceeds"], "33750.00")

    def test_calculate_mvp_summary_combines_housing_and_manual_summaries(self) -> None:
        connection = initialise_database(":memory:")
        upsert_baseline_scenario(connection)
        add_manual_summary(connection, "baseline", "income", "Alex salary", Decimal("4000"), "monthly")
        add_manual_summary(connection, "baseline", "expense", "Bills", Decimal("1200"), "monthly")

        result = calculate_mvp_summary(
            connection,
            "baseline",
            sale_price=Decimal("300000"),
            house_price=Decimal("350000"),
            combined_gross_income=Decimal("90000"),
            persist=True,
        )
        outputs = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM calculator_output WHERE calculator = 'household_summary'").fetchall()
        }
        connection.close()

        self.assertEqual(result.alex_income.net_income_monthly, Decimal("3226.31"))
        self.assertEqual(result.household.monthly_net, Decimal("-4249.04"))
        self.assertEqual(result.housing.affordability.high_max_purchase_price, Decimal("440000.00"))
        self.assertEqual(outputs["monthly_net"], "-4249.04")


if __name__ == "__main__":
    unittest.main()
