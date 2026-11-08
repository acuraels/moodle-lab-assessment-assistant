import copy
import unittest

from assessment_contract.schemas import RubricCriterion
from ml_service.grounding import GroundedAssessment, GroundingError, validate_and_adapt


SUBMISSION = "Отчёт\r\ndef mean(values):\r\n    return sum(values) / len(values)\r\nПояснение решения."


def rubric(*maxima):
    return [RubricCriterion(name=f"Критерий {index + 1}", max_score=value)
            for index, value in enumerate(maxima or (4, 6))]


def assessment(*scores):
    return {"criteria": [
        {"criterion_index": index, "evidence": ["return sum(values) / len(values)"],
         "comment": "Вывод относится к процитированному фрагменту.", "verdict": "met", "score": score}
        for index, score in enumerate(scores or (4, 6))
    ]}


class GroundingTests(unittest.TestCase):
    def test_source_quotes_and_teacher_rubric_are_restored_without_mutation(self):
        scale = rubric()
        draft = assessment()
        original = copy.deepcopy(draft)
        original_scale = [item.model_dump() for item in scale]
        result = validate_and_adapt(draft, scale, SUBMISSION)
        self.assertEqual(result.score, 10)
        self.assertEqual(result.max_score, 10)
        self.assertEqual([row.name for row in result.criteria], [row.name for row in scale])
        self.assertIn("строки извлечённого текста 3", result.criteria[0].comment)
        self.assertIn("«return sum(values) / len(values)»", result.criteria[0].comment)
        self.assertIn("выполнено полностью: 2", result.conclusion)
        self.assertEqual(draft, original)
        self.assertEqual([item.model_dump() for item in scale], original_scale)

    def test_whitespace_equivalence_preserves_original_source_in_comment(self):
        draft = assessment()
        draft["criteria"][0]["evidence"] = ["def\tmean(values):\nreturn  sum(values) /\u00a0len(values)"]
        result = validate_and_adapt(draft, rubric(), SUBMISSION)
        self.assertIn("строки извлечённого текста 2–3", result.criteria[0].comment)
        self.assertIn("def mean(values):\r\n    return sum(values) / len(values)", result.criteria[0].comment)

    def test_invented_or_reference_only_quotes_are_rejected_with_safe_hint(self):
        for quote in ("raise ValueError('empty')", "эталон содержит правильную обработку", "RETURN sum(values) / len(values)", "return sum(values) ÷ len(values)", " \n\t"):
            with self.subTest(quote=quote):
                draft = assessment()
                draft["criteria"][0]["evidence"] = [quote]
                with self.assertRaises(GroundingError) as caught:
                    validate_and_adapt(draft, rubric(), SUBMISSION)
                self.assertEqual(caught.exception.code, "evidence_not_found")
                self.assertEqual(caught.exception.criterion_index, 0)
                self.assertNotIn(quote, str(caught.exception))

    def test_missing_duplicate_and_out_of_order_criteria_are_rejected(self):
        for indices, expected_code in (([0], "criterion_count"), ([0, 0], "criterion_order"), ([1, 0], "criterion_order")):
            with self.subTest(indices=indices):
                draft = assessment()
                draft["criteria"] = draft["criteria"][:len(indices)]
                for row, index in zip(draft["criteria"], indices):
                    row["criterion_index"] = index
                with self.assertRaises(GroundingError) as caught:
                    validate_and_adapt(draft, rubric(), SUBMISSION)
                self.assertEqual(caught.exception.code, expected_code)

    def test_invalid_score_types_and_bounds_are_not_coerced(self):
        for score in (True, "4", -1, float("nan"), float("inf"), 1_000_001):
            with self.subTest(score=score):
                draft = assessment()
                draft["criteria"][0]["score"] = score
                with self.assertRaises(GroundingError) as caught:
                    validate_and_adapt(draft, rubric(), SUBMISSION)
                self.assertEqual(caught.exception.code, "invalid_assessment")
        draft = assessment(5, 6)
        with self.assertRaises(GroundingError) as caught:
            validate_and_adapt(draft, rubric(), SUBMISSION)
        self.assertEqual(caught.exception.code, "score_out_of_range")

    def test_verdict_must_agree_with_score(self):
        for verdict, score in (("met", 3), ("not_met", 1), ("partial", 0), ("partial", 4)):
            with self.subTest(verdict=verdict, score=score):
                draft = assessment()
                draft["criteria"][0].update(verdict=verdict, score=score)
                with self.assertRaises(GroundingError) as caught:
                    validate_and_adapt(draft, rubric(), SUBMISSION)
                self.assertEqual(caught.exception.code, "verdict_score_mismatch")

    def test_decimal_totals_and_partial_summary(self):
        draft = assessment(0.1, 0.2)
        draft["criteria"][0]["verdict"] = "partial"
        result = validate_and_adapt(draft, rubric(0.3, 0.2), SUBMISSION)
        self.assertEqual(result.score, 0.3)
        self.assertEqual(result.max_score, 0.5)
        self.assertIn("Критерий 1", result.conclusion)
        self.assertIn("частично: 1", result.conclusion)

    def test_zero_maximum_supports_met_or_not_met_but_not_partial(self):
        for verdict in ("met", "not_met"):
            draft = assessment(0, 6)
            draft["criteria"][0]["verdict"] = verdict
            self.assertEqual(validate_and_adapt(draft, rubric(0, 6), SUBMISSION).score, 6)
        draft["criteria"][0]["verdict"] = "partial"
        with self.assertRaises(GroundingError) as caught:
            validate_and_adapt(draft, rubric(0, 6), SUBMISSION)
        self.assertEqual(caught.exception.code, "verdict_score_mismatch")

    def test_rubric_is_required_and_extra_scale_fields_are_rejected(self):
        with self.assertRaises(GroundingError) as caught:
            validate_and_adapt(assessment(), [], SUBMISSION)
        self.assertEqual(caught.exception.code, "rubric_required")
        draft = assessment()
        draft["criteria"][0]["max_score"] = 100
        with self.assertRaises(GroundingError) as caught:
            validate_and_adapt(draft, rubric(), SUBMISSION)
        self.assertEqual(caught.exception.code, "invalid_assessment")

    def test_quote_and_comment_limits_are_preserved(self):
        for key, value in (("evidence", ["x" * 2001]), ("comment", "x" * 3001), ("evidence", []), ("evidence", ["x"] * 4)):
            with self.subTest(key=key, size=len(value)):
                draft = assessment()
                draft["criteria"][0][key] = value
                with self.assertRaises(GroundingError):
                    validate_and_adapt(draft, rubric(), SUBMISSION)

    def test_large_source_whitespace_does_not_expand_public_comment(self):
        draft = assessment()
        source = "return" + " " * 20_000 + "sum(values) / len(values)"
        result = validate_and_adapt(draft, rubric(), source)
        self.assertLess(len(result.criteria[0].comment), 10_000)
        self.assertIn("«return sum(values) / len(values)»", result.criteria[0].comment)

    def test_validated_model_instance_is_accepted_without_modification(self):
        draft = GroundedAssessment.model_validate(assessment())
        before = draft.model_dump()
        validate_and_adapt(draft, rubric(), SUBMISSION)
        self.assertEqual(draft.model_dump(), before)


if __name__ == "__main__":
    unittest.main()
