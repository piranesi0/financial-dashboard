import unittest

from financials.scenario import (
    assumption_decimal,
    create_scenario,
    get_assumptions,
    list_scenarios,
    set_assumption,
)
from financials.schema import initialise_database
from financials.seeds import upsert_baseline_scenario


class ScenarioTest(unittest.TestCase):
    def test_create_list_and_set_assumption(self) -> None:
        connection = initialise_database(":memory:")
        upsert_baseline_scenario(connection)
        scenario_id = create_scenario(connection, "test", "Test scenario")
        set_assumption(connection, "test", "housing", "flat_mortgage_balance", "250000", "GBP")

        scenarios = {row["name"]: row["id"] for row in list_scenarios(connection)}
        assumptions = get_assumptions(connection, "test")
        connection.close()

        self.assertEqual(scenarios["test"], scenario_id)
        self.assertEqual(assumption_decimal(assumptions, "housing", "flat_mortgage_balance"), 250000)


if __name__ == "__main__":
    unittest.main()
