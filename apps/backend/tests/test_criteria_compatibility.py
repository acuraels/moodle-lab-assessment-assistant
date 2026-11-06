import copy
import unittest

from pydantic import ValidationError

from app.schemas.attempts import AIResultResponse, CriterionResponse


class CriteriaCompatibilityTests(unittest.TestCase):
    def result(self, criteria):
        return AIResultResponse(
            attempt_id="legacy-attempt",
            status="ai_checked",
            score=8.5,
            max_score=10,
            criteria=criteria,
        ).model_dump(mode="json")

    def test_legacy_result_has_explicit_nulls_without_inventing_maximum(self):
        stored = [{"name": "Algorithm", "score": 4.25}]
        before = copy.deepcopy(stored)
        result = self.result(stored)
        self.assertEqual(result["criteria"], [{
            "name": "Algorithm", "score": 4.25,
            "max_score": None, "comment": None,
        }])
        self.assertEqual(result["max_score"], 10)
        self.assertEqual(stored, before)

    def test_new_result_preserves_all_values(self):
        stored = [{"name": "Algorithm", "score": 4.25,
                   "max_score": 5, "comment": "Check edge cases"}]
        self.assertEqual(self.result(stored)["criteria"], stored)

    def test_explicit_nulls_are_supported(self):
        stored = [{"name": "Algorithm", "score": 0,
                   "max_score": None, "comment": None}]
        self.assertEqual(self.result(stored)["criteria"], stored)

    def test_zero_and_empty_comment_are_not_replaced(self):
        stored = [{"name": "Algorithm", "score": 0,
                   "max_score": 0, "comment": ""}]
        self.assertEqual(self.result(stored)["criteria"], stored)

    def test_partial_and_mixed_versions(self):
        rows = self.result([
            {"name": "Old", "score": 2, "comment": "Keep this"},
            {"name": "New", "score": 3, "max_score": 5},
        ])["criteria"]
        self.assertEqual(rows[0]["comment"], "Keep this")
        self.assertIsNone(rows[0]["max_score"])
        self.assertEqual(rows[1]["max_score"], 5)
        self.assertIsNone(rows[1]["comment"])

    def test_empty_results_and_required_fields(self):
        self.assertEqual(self.result([])["criteria"], [])
        for value in ({"score": 2}, {"name": "Missing score"},
                      {"name": "Bad score", "score": "invalid"}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                CriterionResponse.model_validate(value)


if __name__ == "__main__":
    unittest.main()
