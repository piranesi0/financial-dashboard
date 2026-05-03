from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from financials.scenario import get_assumptions
from financials.schema import connect_database, initialise_database
from financials.seeds import upsert_baseline_scenario
from financials.summaries import add_manual_summary
from financials.web import FinancialsWebApp


class WebTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "financials.sqlite"
        connection = initialise_database(self.database)
        upsert_baseline_scenario(connection)
        add_manual_summary(connection, "baseline", "income", "Alex salary", Decimal("4000"), "monthly")
        connection.close()
        self.app = FinancialsWebApp(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_render_variables_includes_all_seeded_assumptions(self) -> None:
        html = self.app.render_variables("baseline")

        self.assertIn("flat_mortgage_balance", html)
        self.assertIn("default_mortgage_rate", html)
        self.assertIn("charly_hourly_rate", html)
        self.assertIn("charly_pension_contribution_rate", html)
        self.assertIn("nursery", html)

    def test_handle_post_updates_variable(self) -> None:
        target, message = self.app.handle_post(
            "/variables",
            "baseline",
            {
                "namespace": ["housing"],
                "key": ["flat_mortgage_balance"],
                "value": ["250000"],
                "unit": ["GBP"],
            },
        )
        connection = connect_database(self.database)
        assumptions = get_assumptions(connection, "baseline")
        connection.close()

        self.assertEqual(target, "/variables")
        self.assertEqual(message, "Variable updated.")
        self.assertEqual(assumptions[("housing", "flat_mortgage_balance")].value, "250000")

    def test_render_summary_uses_database_values(self) -> None:
        html = self.app.render_summary("baseline")

        self.assertIn("Dashboard", html)
        self.assertIn("Monthly income", html)
        # setUp adds £4,000 salary; baseline seed adds £1,144 rent income → £5,144 total
        self.assertIn("£5,144.00", html)


    def test_delete_manual_summary_via_post(self) -> None:
        connection = connect_database(self.database)
        add_manual_summary(connection, "baseline", "expense", "TestEntryUniqueABC", Decimal("99"), "monthly")
        entry_id = connection.execute(
            "SELECT id FROM manual_summary WHERE category='TestEntryUniqueABC'"
        ).fetchone()["id"]
        connection.close()

        target, message = self.app.handle_post(
            "/manual-summaries",
            "baseline",
            {"_action": ["delete"], "id": [str(entry_id)]},
        )

        connection = connect_database(self.database)
        categories_after = [
            row["category"]
            for row in connection.execute(
                "SELECT category FROM manual_summary WHERE scope='expense'"
            ).fetchall()
        ]
        connection.close()

        self.assertEqual(target, "/expenses")
        self.assertEqual(message, "Entry deleted.")
        self.assertNotIn("TestEntryUniqueABC", categories_after)

    def test_render_expenses_shows_seeded_bills(self) -> None:
        html = self.app.render_expenses("baseline")

        self.assertIn("Flat rental income", html)
        self.assertIn("Flat mortgage", html)
        self.assertIn("Car insurance", html)

    def test_render_alex_shows_income_breakdown(self) -> None:
        html = self.app.render_alex("baseline")

        self.assertIn("Alex Income", html)
        self.assertIn("Gross employment", html)
        self.assertIn("£3,464.98", html)

    def test_render_charly_shows_all_scenarios(self) -> None:
        html = self.app.render_charly("baseline")

        self.assertIn("Charly Income", html)
        self.assertIn("Part-time", html)
        self.assertIn("Full-time", html)
        self.assertIn("Flexible", html)
        self.assertIn("Nursery", html)

    def test_render_flat_shows_rent_and_mortgage(self) -> None:
        html = self.app.render_flat("baseline")

        self.assertIn("Flat", html)
        self.assertIn("£1,144.00", html)

    def test_render_sale_shows_proceeds(self) -> None:
        html = self.app.render_sale("baseline")

        self.assertIn("Flat Sale", html)
        self.assertIn("Net proceeds", html)

    def test_render_purchase_shows_mortgage_and_affordability(self) -> None:
        html = self.app.render_purchase("baseline")

        self.assertIn("House Purchase", html)
        self.assertIn("Monthly payment", html)
        self.assertIn("Combined gross", html)

    def test_set_charly_hours_via_post(self) -> None:
        target, message = self.app.handle_post(
            "/charly",
            "baseline",
            {"_action": ["set_hours"], "hours": ["37.5"]},
        )
        connection = connect_database(self.database)
        from financials.scenario import get_assumptions
        assumptions = get_assumptions(connection, "baseline")
        connection.close()

        self.assertEqual(target, "/charly")
        self.assertIn("37.5", message)
        self.assertEqual(assumptions[("income", "charly_weekly_hours")].value, "37.5")


if __name__ == "__main__":
    unittest.main()
