import unittest

from pydantic import ValidationError

from assessment_contract.rubric import parse_rubric, validate_result_for_rubric
from assessment_contract.schemas import EvaluationRequest, EvaluationResult


class ContractTests(unittest.TestCase):
    def scored(self, **changes):
        value = {"score": 1.5, "max_score": 2, "conclusion": "Есть замечание.", "criteria": [
            {"name": "Алгоритм", "score": 1.5, "max_score": 2, "comment": "Не разобран пустой ввод."}
        ]}
        value.update(changes)
        return value

    def test_numeric_assessment_preserves_explicit_teacher_scale(self):
        rubric = parse_rubric('{"criteria":[{"name":"Алгоритм","max_score":2}]}')
        result = EvaluationResult.model_validate(self.scored())
        self.assertIs(validate_result_for_rubric(result, rubric), result)

    def test_prose_or_invalid_scale_never_authorizes_numbers(self):
        for value in [None, "Максимум 10 баллов", '{"criteria":[]}',
                      '{"criteria":[{"name":"X","max_score":true}]}',
                      '{"criteria":[{"name":"X","max_score":2},{"name":"X","max_score":3}]}']:
            with self.subTest(value=value):
                self.assertIsNone(parse_rubric(value))
        with self.assertRaises(ValueError):
            validate_result_for_rubric(EvaluationResult.model_validate(self.scored()), None)

    def test_empty_rubric_accepts_only_qualitative_result(self):
        result = EvaluationResult(score=None, max_score=None, conclusion="Шкала не задана.", criteria=[])
        self.assertIs(validate_result_for_rubric(result, None), result)
        with self.assertRaises(ValidationError):
            EvaluationResult.model_validate(self.scored(criteria=[]))

    def test_invalid_numeric_values_and_totals_are_rejected(self):
        for score in [-1, 3, float("nan"), float("inf"), True, "1.5", 0.5]:
            with self.subTest(score=score), self.assertRaises(ValidationError):
                EvaluationResult.model_validate(self.scored(score=score))

    def test_changed_teacher_scale_is_rejected(self):
        rubric = parse_rubric('{"criteria":[{"name":"Алгоритм","max_score":3}]}')
        with self.assertRaises(ValueError):
            validate_result_for_rubric(EvaluationResult.model_validate(self.scored()), rubric)

    def test_materials_cannot_cross_categories(self):
        with self.assertRaises(ValidationError):
            EvaluationRequest(attempt_id="a", lab_id="b", title="Лаба", settings_version=1,
                              materials={"grading_criteria": {"file_key": "reference_work"}})


if __name__ == "__main__":
    unittest.main()
