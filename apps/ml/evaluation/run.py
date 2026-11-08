#!/usr/bin/env python3
"""Serial synthetic grading evaluation with real Ollama and fixture text extraction.

Expected answers are read only by the comparison function; model input contains
only the fixture's EvaluationRequest and submission_text. This runner does not
exercise PDF/DOCX parsing, backend queues, persistence, or frontend rendering.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.parse import urlsplit

import httpx

from assessment_contract.schemas import EvaluationRequest
from ml_service import pipeline
from ml_service.config import Settings
from ml_service.errors import EvaluationFailure
from ml_service.extraction import DocumentInput, TXT
from ml_service.pipeline import Evaluator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, payload: dict) -> None:
    """Replace one owner-only JSON result after each case, preserving partial runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".grading-evaluation-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def distance_to_range(value: float, bounds: list[float]) -> float:
    return max(bounds[0] - value, 0.0, value - bounds[1])


def compare(actual: dict, expected: dict) -> dict:
    """Score numerical agreement only; factual prose needs independent review."""
    errors = []
    criterion_errors = []
    if not str(actual.get("conclusion") or "").strip():
        errors.append("empty_conclusion")
    if expected["mode"] == "qualitative":
        if actual.get("score") is not None or actual.get("max_score") is not None or actual.get("criteria") != []:
            errors.append("invented_numeric_scale")
        return {"passed": not errors, "errors": errors, "overall_absolute_error": None,
                "criterion_absolute_errors": [], "criteria_in_range": 0, "criteria_total": 0}
    actual_rows = actual.get("criteria", [])
    expected_rows = expected["criteria"]
    overall_error = None
    if not finite_number(actual.get("score")):
        errors.append("missing_numeric_score")
    else:
        overall_error = distance_to_range(actual["score"], expected["score_range"])
        if overall_error > 1e-6:
            errors.append("overall_score_out_of_range")
    if actual.get("max_score") != expected["max_score"]:
        errors.append("overall_maximum_changed")
    if len(actual_rows) != len(expected_rows):
        errors.append("criterion_count_changed")
    criteria_in_range = 0
    for index, reference in enumerate(expected_rows):
        if index >= len(actual_rows):
            criterion_errors.append(None)
            continue
        row = actual_rows[index]
        same_criterion = row.get("name") == reference["name"] and row.get("max_score") == reference["max_score"]
        if not same_criterion:
            errors.append(f"criterion_{index}_changed")
        if not finite_number(row.get("score")):
            errors.append(f"criterion_{index}_score_missing")
            criterion_errors.append(None)
            continue
        delta = distance_to_range(row["score"], reference["score_range"])
        criterion_errors.append(delta)
        if same_criterion and delta <= 1e-6:
            criteria_in_range += 1
        else:
            errors.append(f"criterion_{index}_score_out_of_range")
    return {"passed": not errors, "errors": errors, "overall_absolute_error": overall_error,
            "criterion_absolute_errors": criterion_errors, "criteria_in_range": criteria_in_range,
            "criteria_total": len(expected_rows)}


def summarize(records: list[dict], planned: int) -> dict:
    valid = [row for row in records if "result" in row]
    numerical = [row["comparison"]["overall_absolute_error"] for row in valid
                 if row["comparison"]["overall_absolute_error"] is not None]
    criterion_errors = [value for row in valid for value in row["comparison"]["criterion_absolute_errors"]
                        if value is not None]
    durations = sorted(row["duration_seconds"] for row in records)
    checks = [row["comparison"]["passed"] for row in valid]
    return {
        "planned_cases_including_repeats": planned,
        "completed_cases": len(records),
        "valid_results": len(valid),
        "failed_requests": len(records) - len(valid),
        "numeric_or_qualitative_agreement_passes": sum(checks),
        "agreement_rate_over_all_completed": sum(checks) / len(records) if records else None,
        "agreement_rate_over_valid_results": sum(checks) / len(valid) if valid else None,
        "result_coverage": len(valid) / planned if planned else None,
        "numeric_cases_with_measured_error": len(numerical),
        "overall_mae_to_expected_range": sum(numerical) / len(numerical) if numerical else None,
        "criterion_mae_to_expected_range": sum(criterion_errors) / len(criterion_errors) if criterion_errors else None,
        "criteria_in_range": sum(row["comparison"]["criteria_in_range"] for row in valid),
        "criteria_total_in_valid_results": sum(row["comparison"]["criteria_total"] for row in valid),
        "median_duration_seconds": (durations[(len(durations) - 1) // 2] + durations[len(durations) // 2]) / 2 if durations else None,
        "total_duration_seconds": sum(durations),
        "all_automated_checks_passed": len(records) == planned and len(valid) == planned and all(checks),
        "factual_feedback_review_required": True,
    }


async def fixture_text(document: DocumentInput, _: Settings) -> str:
    return document.data.decode("utf-8")


async def runtime_metadata(url: str, model: str) -> dict:
    info = {"model_requested": model}
    async with httpx.AsyncClient(base_url=url.rstrip("/"), trust_env=False, timeout=10) as client:
        for label, endpoint in (("runtime", "/api/version"), ("models", "/api/tags")):
            try:
                response = await client.get(endpoint)
                response.raise_for_status()
                value = response.json()
                if label == "runtime":
                    info["ollama_version"] = value.get("version")
                else:
                    selected = next((item for item in value.get("models", [])
                                     if model in (item.get("name"), item.get("model"))), None)
                    info["model_found"] = selected is not None
                    if selected is not None:
                        info["model_digest"] = selected.get("digest")
                        info["model_details"] = selected.get("details")
                        info["model_size_bytes"] = selected.get("size")
            except (httpx.HTTPError, ValueError, AttributeError, TypeError) as exc:
                info[label + "_lookup_error"] = type(exc).__name__
    return info


async def run(args: argparse.Namespace) -> int:
    data_bytes = args.cases.read_bytes()
    dataset = json.loads(data_bytes)
    selected = [case for case in dataset["cases"] if args.split == "all" or case["split"] == args.split]
    requested_ids = set(args.case or [])
    if requested_ids:
        selected = [case for case in selected if case["id"] in requested_ids]
        missing = requested_ids - {case["id"] for case in selected}
        if missing:
            raise ValueError("Unknown case IDs for selected split: " + ", ".join(sorted(missing)))
    if not selected:
        raise ValueError("No cases selected")
    if len({case["id"] for case in selected}) != len(selected):
        raise ValueError("Dataset contains duplicate IDs")
    # Validate request inputs before making any model call. Labels are separate.
    requests = {case["id"]: EvaluationRequest.model_validate(case["metadata"]) for case in selected}
    settings = Settings(_env_file=None, ollama_url=args.ollama_url, ollama_model=args.model,
                        context_tokens=args.context_tokens, output_tokens=args.output_tokens)
    source = inspect.getsource(pipeline).encode("utf-8")
    package_directory = Path(inspect.getfile(pipeline)).resolve().parent
    code_sha256 = {
        str(path.relative_to(package_directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(package_directory.rglob("*.py"))
    }
    planned = len(selected) * args.repeat
    report = {
        "started_at": utc_now(), "completed_at": None,
        "dataset": {"path": str(args.cases), "sha256": hashlib.sha256(data_bytes).hexdigest(),
                    "synthetic": dataset.get("synthetic"), "label_source": dataset.get("label_source"),
                    "split": args.split, "case_ids": [case["id"] for case in selected]},
        "configuration": {"model": args.model, "context_tokens": args.context_tokens,
                          "output_tokens": args.output_tokens, "repeat": args.repeat,
                          "review_enabled": getattr(settings, "review_enabled", False),
                          "prompt_version": args.prompt_version,
                          "implementation_prompt_version": getattr(pipeline, "PROMPT_VERSION", None),
                          "pipeline_sha256": hashlib.sha256(source).hexdigest(),
                          "code_sha256": code_sha256},
        "method": {"real_ollama_generation": True, "extraction": "fixture UTF-8 text; PDF/DOCX parser bypassed",
                   "expected_labels_sent_to_model": False, "student_code_executed": False,
                   "evaluation_scope": "synthetic numerical regression, not general grading accuracy"},
        "runtime": await runtime_metadata(args.ollama_url, args.model), "results": [],
        "summary": summarize([], planned),
    }
    save(args.output, report)
    evaluator = Evaluator(settings, extractor=fixture_text)
    try:
        for repeat in range(1, args.repeat + 1):
            for case in selected:
                print(f"[{len(report['results']) + 1}/{planned}] {case['id']} repeat={repeat}", flush=True)
                started = time.monotonic()
                record = {"case_id": case["id"], "split": case["split"], "family": case["family"],
                          "repeat": repeat, "started_at": utc_now()}
                try:
                    actual = await evaluator.evaluate(
                        requests[case["id"]], DocumentInput(case["id"] + ".txt", TXT, case["submission_text"].encode("utf-8")), {})
                    actual_data = actual.model_dump()
                    comparison = compare(actual_data, case["expected"])
                    # Store a valid result and its comparison together. A bad
                    # future fixture must become a counted runner failure, not
                    # leave a half-written record that breaks summarize().
                    record.update(result=actual_data, comparison=comparison,
                                  expected_for_offline_review=case["expected"])
                except EvaluationFailure as exc:
                    record["error"] = {"code": exc.code, "message": exc.message, "retryable": exc.retryable}
                except Exception as exc:
                    # Keep a reproducible failure count without leaking arbitrary tracebacks.
                    record["error"] = {"code": "RUNNER_EXCEPTION", "exception_type": type(exc).__name__}
                record["duration_seconds"] = round(time.monotonic() - started, 3)
                report["results"].append(record)
                report["summary"] = summarize(report["results"], planned)
                save(args.output, report)
                if "result" in record:
                    print(f"  score={record['result']['score']}/{record['result']['max_score']} "
                          f"agreement={record['comparison']['passed']} duration={record['duration_seconds']}s", flush=True)
                else:
                    print(f"  error={record['error']['code']} duration={record['duration_seconds']}s", flush=True)
    finally:
        await evaluator.close()
        report["completed_at"] = utc_now()
        report["summary"] = summarize(report["results"], planned)
        save(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
    print("Report:", args.output, flush=True)
    return 0 if report["summary"]["all_automated_checks_passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--split", choices=("development", "holdout", "all"), default="development")
    parser.add_argument("--ollama-url", required=True, help="Ollama HTTP(S) origin; never a cloud LLM API")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True, help="New JSON report path outside the repository")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--case", action="append", help="Case ID; may be supplied multiple times")
    parser.add_argument("--context-tokens", type=int, default=8192)
    parser.add_argument("--output-tokens", type=int, default=2048)
    parser.add_argument("--prompt-version", default="unspecified")
    args = parser.parse_args()
    args.output = args.output.expanduser().resolve()
    args.cases = args.cases.expanduser().resolve()
    if args.output.exists():
        parser.error("--output already exists; use a fresh path to preserve the previous experiment")
    if not 1 <= args.repeat <= 20:
        parser.error("--repeat must be between 1 and 20")
    parsed = urlsplit(args.ollama_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error("--ollama-url must be an HTTP(S) URL without credentials, query, or fragment")
    # In a checkout, prevent committing model outputs alongside fixtures. In a
    # container the mounted /evaluation has no .git, so the caller chooses /results.
    checkout = next((parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists()), None)
    if checkout is not None and args.output.is_relative_to(checkout):
        parser.error("--output must be outside the repository")
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Interrupted; completed cases remain in the report", file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError) as exc:
        print("Evaluation setup failed:", type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
