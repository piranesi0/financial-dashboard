import unittest

from financials.schema import initialise_database
from financials.seeds import upsert_baseline_scenario


class SeedsTest(unittest.TestCase):
    def test_upsert_baseline_scenario_adds_assumptions(self) -> None:
        connection = initialise_database(":memory:")
        scenario_id = upsert_baseline_scenario(connection)

        scenario = connection.execute(
            "SELECT name FROM scenario WHERE id = ?",
            (scenario_id,),
        ).fetchone()
        assumptions = {
            (row["namespace"], row["key"]): (row["value"], row["value_type"])
            for row in connection.execute(
                "SELECT namespace, key, value, value_type FROM assumption WHERE scenario_id = ?",
                (scenario_id,),
            ).fetchall()
        }
        expenses = {
            row["category"]: row["amount"]
            for row in connection.execute(
                "SELECT category, amount FROM manual_summary WHERE scenario_id = ? AND scope = 'expense'",
                (scenario_id,),
            ).fetchall()
        }
        income = {
            row["category"]: row["amount"]
            for row in connection.execute(
                "SELECT category, amount FROM manual_summary WHERE scenario_id = ? AND scope = 'income'",
                (scenario_id,),
            ).fetchall()
        }
        connection.close()

        self.assertEqual(scenario["name"], "baseline")
        self.assertEqual(assumptions[("housing", "flat_mortgage_balance")], ("259000", "money"))
        self.assertEqual(assumptions[("housing", "default_mortgage_rate")], ("0.045", "percent"))
        self.assertEqual(assumptions[("housing", "default_combined_gross_income")], ("0", "money"))
        self.assertEqual(assumptions[("income", "charly_hourly_rate")], ("21.90", "money"))
        self.assertEqual(assumptions[("income", "alex_select_points")], ("8622.3544", "decimal"))
        self.assertEqual(assumptions[("categorisation", "projects_scope")], ("personal", "text"))
        self.assertEqual(expenses["Groceries"], "600.00")
        self.assertEqual(expenses["Subscriptions"], "50.00")
        self.assertEqual(expenses["Flat mortgage"], "1124.10")
        self.assertEqual(expenses["Car insurance"], "51.14")
        self.assertEqual(expenses["Pet insurance"], "31.41")
        self.assertEqual(income["Flat rental income"], "1144.00")


if __name__ == "__main__":
    unittest.main()
