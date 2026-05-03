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
        self.assertIn("Household income", html)
        # Alex net income is £3,464.98
        self.assertIn("£3,464.98", html)


    def test_delete_manual_summary_via_post(self) -> None:
        connection = connect_database(self.database)
        add_manual_summary(connection, "baseline", "expense", "TestEntryUniqueABC", Decimal("99"), "monthly")
        entry_id = connection.execute(
            "SELECT id FROM manual_summary WHERE category='TestEntryUniqueABC'"
        ).fetchone()["id"]
        connection.close()

        target, message = self.app.handle_post(
            "/tracker",
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

        self.assertEqual(target, "/tracker")
        self.assertEqual(message, "Entry deleted.")
        self.assertNotIn("TestEntryUniqueABC", categories_after)

    def test_render_tracker_shows_seeded_bills(self) -> None:
        html = self.app.render_tracker("baseline")

        self.assertIn("Flat rental income", html)
        self.assertIn("Flat mortgage", html)
        self.assertIn("Car insurance", html)

    def test_render_alex_shows_income_breakdown(self) -> None:
        html = self.app.render_alex("baseline")

        self.assertIn("Alex Income", html)
        self.assertIn("Gross employment", html)
        self.assertIn("£3,226.31", html)

    def test_render_charly_shows_all_scenarios(self) -> None:
        html = self.app.render_charly("baseline")

        self.assertIn("Charly Income", html)
        self.assertIn("Part-time", html)
        self.assertIn("Full-time", html)
        self.assertIn("Flexible", html)
        self.assertIn("Nursery", html)

    def test_render_housing_current_shows_keep_in_place(self) -> None:
        html = self.app.render_housing("baseline", tab="current")

        self.assertIn("Housing", html)
        self.assertIn("keep-in-place", html)
        self.assertIn("£250.00", html)
        self.assertIn("£1,144.00", html)

    def test_render_housing_flat_shows_living_costs_and_sale(self) -> None:
        html = self.app.render_housing("baseline", tab="flat")

        self.assertIn("Housing", html)
        self.assertIn("Living in the flat", html)
        self.assertIn("Total living cost", html)
        self.assertIn("Council tax", html)
        self.assertIn("Household bills", html)
        self.assertIn("Net proceeds", html)
        self.assertIn("Sale proceeds", html)
        self.assertNotIn("Rental income", html)

    def test_render_housing_house_shows_mortgage_and_affordability(self) -> None:
        html = self.app.render_housing("baseline", tab="house")

        self.assertIn("House Purchase", html)
        self.assertIn("Monthly payment", html)
        self.assertIn("Combined gross", html)
        self.assertIn("Council tax", html)
        self.assertIn("Household bills", html)
        self.assertIn("Total living cost", html)

    def test_update_manual_summary_via_post(self) -> None:
        connection = connect_database(self.database)
        add_manual_summary(connection, "baseline", "expense", "OldCategory", Decimal("50"), "monthly", group_name="Bills")
        entry_id = connection.execute(
            "SELECT id FROM manual_summary WHERE category='OldCategory'"
        ).fetchone()["id"]
        connection.close()

        target, message = self.app.handle_post(
            "/tracker",
            "baseline",
            {"_action": ["update"], "id": [str(entry_id)], "category": ["NewCategory"], "amount": ["75"], "group_name": ["Household"]},
        )

        connection = connect_database(self.database)
        row = connection.execute("SELECT category, amount, group_name FROM manual_summary WHERE id = ?", (entry_id,)).fetchone()
        connection.close()

        self.assertEqual(target, "/tracker")
        self.assertEqual(message, "Entry updated.")
        self.assertEqual(row["category"], "NewCategory")
        self.assertEqual(row["amount"], "75")
        self.assertEqual(row["group_name"], "Household")

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


    def test_toggle_nursery_via_post(self) -> None:
        target, message = self.app.handle_post(
            "/charly",
            "baseline",
            {"_action": ["toggle_nursery"], "enabled": ["false"]},
        )
        connection = connect_database(self.database)
        from financials.scenario import get_assumptions, assumption_bool
        assumptions = get_assumptions(connection, "baseline")
        connection.close()

        self.assertEqual(target, "/charly")
        self.assertIn("disabled", message)
        self.assertFalse(assumption_bool(assumptions, "nursery", "enabled"))

    def test_nursery_disabled_zeroes_costs_on_charly_page(self) -> None:
        self.app.handle_post(
            "/charly", "baseline",
            {"_action": ["toggle_nursery"], "enabled": ["false"]},
        )
        html = self.app.render_charly("baseline")
        self.assertIn("Disabled", html)
        self.assertIn("disabled", html)

    def test_nursery_enabled_shows_calculator(self) -> None:
        html = self.app.render_charly("baseline")
        self.assertIn("Nursery calculator", html)
        self.assertIn("Enabled", html)


if __name__ == "__main__":
    unittest.main()
