import unittest

from financials.schema import initialise_database


class SchemaTest(unittest.TestCase):
    def test_initialise_database_creates_core_tables(self) -> None:
        connection = initialise_database(":memory:")
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        connection.close()

        self.assertIn("source_file", tables)
        self.assertIn("workbook_sheet", tables)
        self.assertIn("scenario", tables)
        self.assertIn("assumption", tables)
        self.assertIn("manual_summary", tables)
        self.assertIn("transaction_raw", tables)
        self.assertIn("calculator_output", tables)


if __name__ == "__main__":
    unittest.main()
