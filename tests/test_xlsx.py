from pathlib import Path
import unittest

from financials.xlsx import column_to_number, excel_serial_date_to_iso, profile_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class XlsxTest(unittest.TestCase):
    def test_column_to_number(self) -> None:
        self.assertEqual(column_to_number("A"), 1)
        self.assertEqual(column_to_number("Z"), 26)
        self.assertEqual(column_to_number("AA"), 27)

    def test_excel_serial_date_to_iso(self) -> None:
        self.assertEqual(excel_serial_date_to_iso("45510"), "2024-08-06")

    def test_profile_current_workbook(self) -> None:
        profile = profile_workbook(PROJECT_ROOT / "sheets" / "Monzo Transactions.xlsx")
        sheet_names = {sheet.name for sheet in profile.sheets}
        self.assertIn("Personal Account Transactions", sheet_names)
        personal_sheet = next(sheet for sheet in profile.sheets if sheet.name == "Personal Account Transactions")
        self.assertGreater(personal_sheet.used_rows, 2000)
        self.assertGreaterEqual(personal_sheet.used_columns, 16)


if __name__ == "__main__":
    unittest.main()
