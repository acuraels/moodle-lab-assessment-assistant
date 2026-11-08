import argparse
import asyncio
import json
from pathlib import Path

from assessment_contract.schemas import EvaluationRequest, MaterialInput
from ml_service.config import Settings
from ml_service.errors import EvaluationFailure
from ml_service.extraction import DOCX, PDF, TXT, DocumentInput
from ml_service.pipeline import Evaluator


def document(path: Path, max_bytes: int) -> DocumentInput:
    content_type = {".pdf": PDF, ".docx": DOCX, ".txt": TXT}.get(path.suffix.lower(), "")
    with path.open("rb") as source:
        data = source.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise EvaluationFailure("FILE_TOO_LARGE", "Документ превышает допустимый размер.", status=413)
    return DocumentInput(path.name, content_type, data)


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    materials = {}
    files = {}
    for category in ("methodical_guide", "grading_criteria", "system_instructions", "reference_work"):
        path = getattr(args, category)
        if path is not None:
            files[category] = document(path, settings.max_file_bytes)
            materials[category] = MaterialInput(file_key=category)
    if not materials:
        materials["methodical_guide"] = MaterialInput(text=args.title)
    metadata = EvaluationRequest(attempt_id="cli", lab_id="cli", title=args.title,
                                 description=args.description, settings_version=1, materials=materials)
    evaluator = Evaluator(settings)
    try:
        submission = document(args.submission, settings.max_file_bytes)
        if submission.content_type not in {PDF, DOCX}:
            raise EvaluationFailure("UNSUPPORTED_FILE_TYPE", "Работа должна быть PDF или DOCX.", status=415)
        result = await evaluator.evaluate(metadata, submission, files)
        print(result.model_dump_json(indent=2))
        return 0
    except EvaluationFailure as exc:
        print(json.dumps(exc.payload(), ensure_ascii=False, indent=2))
        return 1
    finally:
        await evaluator.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Проверить один документ реальной локальной моделью Ollama")
    parser.add_argument("submission", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default=None)
    for category in ("methodical_guide", "grading_criteria", "system_instructions", "reference_work"):
        parser.add_argument("--" + category.replace("_", "-"), type=Path)
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except EvaluationFailure as exc:
        print(json.dumps(exc.payload(), ensure_ascii=False, indent=2))
        raise SystemExit(1)
    except OSError:
        parser.exit(1, "Не удалось прочитать локальный файл. Проверьте путь и права доступа.\n")


if __name__ == "__main__":
    main()
