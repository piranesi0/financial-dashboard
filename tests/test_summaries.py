from decimal import Decimal
import unittest

from financials.schema import initialise_database
from financials.scenario import create_scenario
from financials.summaries import (
    add_manual_summary,
    calculate_household_summary,
    delete_manual_summary,
    list_manual_summaries,
    monthly_amount,
)


class SummariesTest(unittest.TestCase):
    def test_monthly_amount_conversion(self) -> None:
        self.assertEqual(monthly_amount(Decimal("1200"), "yearly"), Decimal("100.00"))
        self.assertEqual(monthly_amount(Decimal("100"), "weekly"), Decimal("433.33"))
        self.assertEqual(monthly_amount(Decimal("50"), "monthly"), Decimal("50.00"))
        self.assertEqual(monthly_amount(Decimal("500"), "one_off"), Decimal("0.00"))

    def test_manual_summary_totals(self) -> None:
        connection = initialise_database(":memory:")
        create_scenario(connection, "test")
        add_manual_summary(connection, "test", "income", "Alex salary", Decimal("4000"), "monthly")
        add_manual_summary(connection, "test", "expense", "Bills", Decimal("1200"), "monthly")
        add_manual_summary(connection, "test", "saving", "Alex pot", Decimal("300"), "monthly")

        summary = calculate_household_summary(list_manual_summaries(connection, "test"))
        connection.close()

        self.assertEqual(summary.monthly_income, Decimal("4000.00"))
        self.assertEqual(summary.monthly_expenses, Decimal("1200.00"))
        self.assertEqual(summary.monthly_savings, Decimal("300.00"))
        self.assertEqual(summary.monthly_net, Decimal("2500.00"))


    def test_delete_manual_summary(self) -> None:
        connection = initialise_database(":memory:")
        create_scenario(connection, "test")
        add_manual_summary(connection, "test", "expense", "Bills", Decimal("100"), "monthly")
        add_manual_summary(connection, "test", "expense", "Food", Decimal("200"), "monthly")

        items_before = list_manual_summaries(connection, "test")
        self.assertEqual(len(items_before), 2)
        bill_id = next(i.id for i in items_before if i.category == "Bills")

        delete_manual_summary(connection, bill_id)
        items_after = list_manual_summaries(connection, "test")
        connection.close()

        self.assertEqual(len(items_after), 1)
        self.assertEqual(items_after[0].category, "Food")

    def test_list_manual_summaries_includes_id(self) -> None:
        connection = initialise_database(":memory:")
        create_scenario(connection, "test")
        add_manual_summary(connection, "test", "income", "Salary", Decimal("3000"), "monthly")
        items = list_manual_summaries(connection, "test")
        connection.close()

        self.assertIsNotNone(items[0].id)
        self.assertIsInstance(items[0].id, int)


if __name__ == "__main__":
    unittest.main()
