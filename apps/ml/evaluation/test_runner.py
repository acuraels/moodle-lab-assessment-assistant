"""Offline regression for reporting malformed future evaluation fixtures."""
import argparse
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch


spec = importlib.util.spec_from_file_location("grading_evaluation_runner", Path(__file__).with_name("run.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerReportingTests(unittest.IsolatedAsyncioTestCase):
    async def test_bad_expected_label_is_counted_without_losing_report(self):
        case = {
            "id": "bad-future-label", "split": "development", "family": "synthetic",
            "metadata": {
                "attempt_id": "test-attempt", "lab_id": "test-lab", "title": "Synthetic test",
                "settings_version": 1, "materials": {"methodical_guide": {"text": "Explain the algorithm."}},
            },
            "submission_text": "Synthetic explanation.",
            "expected": {},  # Missing mode must not leave a partial success row.
        }
        actual = {"score": None, "max_score": None, "criteria": [], "conclusion": "Synthetic feedback."}
        evaluator = SimpleNamespace(
            evaluate=AsyncMock(return_value=SimpleNamespace(model_dump=lambda: actual)),
            close=AsyncMock(),
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cases_file = root / "cases.json"
            cases_file.write_text(json.dumps({"cases": [case], "synthetic": True}))
            output = root / "result.json"
            args = argparse.Namespace(
                cases=cases_file, output=output, split="development", case=None, repeat=1,
                ollama_url="http://not-contacted.invalid", model="synthetic-model",
                context_tokens=8192, output_tokens=2048, prompt_version="offline-test",
            )
            with patch.object(runner, "Evaluator", return_value=evaluator), patch.object(
                runner, "runtime_metadata", new=AsyncMock(return_value={"offline_test": True})
            ), redirect_stdout(StringIO()):
                exit_code = await runner.run(args)
            report = json.loads(output.read_text())
        self.assertEqual(exit_code, 1)
        self.assertEqual(report["summary"]["failed_requests"], 1)
        self.assertEqual(report["summary"]["valid_results"], 0)
        self.assertEqual(report["summary"]["result_coverage"], 0)
        self.assertFalse(report["summary"]["all_automated_checks_passed"])
        self.assertEqual(report["results"][0]["error"]["code"], "RUNNER_EXCEPTION")
        self.assertNotIn("result", report["results"][0])
        self.assertNotIn("comparison", report["results"][0])
        evaluator.evaluate.assert_awaited_once()
        evaluator.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
