"""Bounded parser process; no persistent document files are written."""
import json
import os
import sys


def main() -> None:
    # Windows has no resource module. A hard wall-clock deadline is enforced by
    # the parent on every platform; Docker additionally bounds container RAM.
    if os.name == "posix":
        import resource
        limit = 1024 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    from ml_service.config import Settings
    from ml_service.errors import EvaluationFailure
    from ml_service.extraction import DocumentInput, extract_document

    content_type, filename, limits_json = sys.argv[1:]
    settings = Settings(_env_file=None, **json.loads(limits_json))
    data = sys.stdin.buffer.read(settings.max_file_bytes + 1)
    try:
        text = extract_document(DocumentInput(filename, content_type, data), settings)
        output = {"text": text}
    except EvaluationFailure as exc:
        output = {"error": {"code": exc.code, "message": exc.message, "status": exc.status}}
    sys.stdout.buffer.write(json.dumps(output, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
