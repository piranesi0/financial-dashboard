from pathlib import Path
import unittest

from financials.profile_store import profile_and_persist_workbook
from financials.schema import initialise_database

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProfileStoreTest(unittest.TestCase):
    def test_profile_and_persist_workbook_records_source_and_sheets(self) -> None:
        connection = initialise_database(":memory:")
        source_file_id = profile_and_persist_workbook(
            connection,
            PROJECT_ROOT / "sheets" / "Charly Pay and Nursery.xlsx",
        )

        source = connection.execute(
            "SELECT path, kind FROM source_file WHERE id = ?",
            (source_file_id,),
        ).fetchone()
        sheets = connection.execute(
            "SELECT name, used_rows, used_columns FROM workbook_sheet WHERE source_file_id = ?",
            (source_file_id,),
        ).fetchall()
        connection.close()

        self.assertEqual(source["kind"], "xlsx")
        self.assertTrue(source["path"].endswith("Charly Pay and Nursery.xlsx"))
        self.assertEqual(len(sheets), 1)
        self.assertEqual(sheets[0]["name"], "Sheet1")
        self.assertEqual(sheets[0]["used_rows"], 77)


if __name__ == "__main__":
    unittest.main()
