import unittest

from reviewer import review


class ReviewerTests(unittest.TestCase):
    def test_amharic_passes(self):
        report = review("ሰላም፣ ዓለም!", "am")
        self.assertTrue(report["passed"])
        self.assertEqual(report["findings"], [])

    def test_oromo_passes(self):
        report = review("Akkam jirtu?", "om")
        self.assertTrue(report["passed"])

    def test_wrong_script_is_error(self):
        report = review("Akkam jirtu?", "am")
        self.assertFalse(report["passed"])
        self.assertEqual(report["findings"][0]["code"], "missing_target_script")

    def test_placeholder_and_spacing_are_reported(self):
        report = review("Akkam  {{NAME}} !", "om")
        codes = {finding["code"] for finding in report["findings"]}
        self.assertEqual(codes, {"placeholder", "repeated_whitespace", "space_before_punctuation"})
        self.assertFalse(report["passed"])

    def test_empty_text_is_error(self):
        report = review("  ", "om")
        self.assertFalse(report["passed"])
        self.assertEqual(report["findings"][0]["code"], "empty_text")


if __name__ == "__main__":
    unittest.main()
