import unittest

from firstaid_app import validators as V
from firstaid_app.config import CATEGORIES


class ValidatorTests(unittest.TestCase):
    def test_severity_accepts_1_to_5(self):
        self.assertEqual([V.severity(x) for x in ("1", " 3 ", "5")], [1, 3, 5])

    def test_severity_rejects_bad_values(self):
        for bad in ("0", "6", "abc", "", "2.5"):
            with self.assertRaises(ValueError):
                V.severity(bad)

    def test_category_by_number_or_name(self):
        self.assertEqual(V.category("2"), CATEGORIES[1])
        self.assertEqual(V.category("burns"), "Burns")
        with self.assertRaises(ValueError):
            V.category("99")

    def test_title_length(self):
        self.assertEqual(V.title("  Burn  "), "Burn")
        for bad in ("ab", "x" * 81):
            with self.assertRaises(ValueError):
                V.title(bad)

    def test_keywords_split_and_lowercase(self):
        self.assertEqual(V.keywords("Burn, HEAT;fire"), ["burn", "heat", "fire"])
        with self.assertRaises(ValueError):
            V.keywords(" , ")

    def test_steps_length(self):
        with self.assertRaises(ValueError):
            V.steps("short")

    def test_yes_no(self):
        self.assertTrue(V.yes_no("Y"))
        self.assertFalse(V.yes_no("no"))
        with self.assertRaises(ValueError):
            V.yes_no("maybe")

    def test_review_date_rules(self):
        self.assertEqual(V.review_date("2026-01-05"), "2026-01-05")
        for bad in ("2999-01-01", "2026-13-45", "yesterday"):
            with self.assertRaises(ValueError):
                V.review_date(bad)

    def test_validate_row_collects_every_error(self):
        _, errors = V.validate_row({"title": "x", "severity": "9"})
        self.assertGreaterEqual(len(errors), 4)
