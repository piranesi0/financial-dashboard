from decimal import Decimal
import unittest

from financials.calculators.nursery import NurseryInput, calculate_nursery


class NurseryTest(unittest.TestCase):
    def test_three_days_with_funded_hours(self) -> None:
        # days=3, daily_cost=70, funded_hours=15, hourly_cost=8.50, hours_per_day=9
        # Weekly gross = 3 × 70 = 210
        # Monthly gross = 210 × 52 / 12 = 910.00
        # Nursery hrs/wk = 3 × 9 = 27; funded applied = min(15, 27) = 15
        # Monthly funded saving = 15 × 8.50 × 38 / 12 = 403.75
        # Monthly net = 910.00 - 403.75 = 506.25
        result = calculate_nursery(NurseryInput(
            days_per_week=Decimal("3"),
            daily_cost=Decimal("70"),
            weekly_funded_hours=Decimal("15"),
            hourly_cost=Decimal("8.50"),
            hours_per_day=Decimal("9"),
        ))

        self.assertEqual(result.weekly_gross_cost, Decimal("210.00"))
        self.assertEqual(result.monthly_gross_cost, Decimal("910.00"))
        self.assertEqual(result.weekly_funded_hours_applied, Decimal("15"))
        self.assertEqual(result.monthly_funded_saving, Decimal("403.75"))
        self.assertEqual(result.monthly_net_cost, Decimal("506.25"))
        self.assertEqual(result.annual_net_cost, Decimal("6075.00"))

    def test_funded_hours_capped_by_nursery_hours(self) -> None:
        # 1 day/week × 9 hrs/day = 9 nursery hrs; funded_hours=15 → applied=9
        result = calculate_nursery(NurseryInput(
            days_per_week=Decimal("1"),
            daily_cost=Decimal("70"),
            weekly_funded_hours=Decimal("15"),
            hourly_cost=Decimal("8.50"),
            hours_per_day=Decimal("9"),
        ))

        self.assertEqual(result.weekly_funded_hours_applied, Decimal("9"))

    def test_no_funded_hours(self) -> None:
        result = calculate_nursery(NurseryInput(
            days_per_week=Decimal("3"),
            daily_cost=Decimal("70"),
            weekly_funded_hours=Decimal("0"),
            hourly_cost=Decimal("8.50"),
            hours_per_day=Decimal("9"),
        ))

        self.assertEqual(result.monthly_funded_saving, Decimal("0.00"))
        self.assertEqual(result.monthly_net_cost, result.monthly_gross_cost)

    def test_five_days_full_week(self) -> None:
        result = calculate_nursery(NurseryInput(
            days_per_week=Decimal("5"),
            daily_cost=Decimal("70"),
            weekly_funded_hours=Decimal("30"),
            hourly_cost=Decimal("8.50"),
            hours_per_day=Decimal("9"),
        ))
        # Weekly gross = 5 × 70 = 350
        # Monthly gross = 350 × 52 / 12 = 1516.67
        # Nursery hrs/wk = 5 × 9 = 45; funded applied = min(30, 45) = 30
        # Monthly funded saving = 30 × 8.50 × 38 / 12 = 807.50
        self.assertEqual(result.weekly_funded_hours_applied, Decimal("30"))
        self.assertEqual(result.monthly_funded_saving, Decimal("807.50"))


if __name__ == "__main__":
    unittest.main()
