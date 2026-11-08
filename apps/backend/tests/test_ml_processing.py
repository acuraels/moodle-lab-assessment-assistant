"""Isolated SQLite/HTTP-mock integration tests, not real GPU or PostgreSQL tests."""

import asyncio
import json
import os
from datetime import timedelta
from unittest.mock import AsyncMock

# Always isolate imports from deployment credentials and databases.
os.environ.update(
    DATABASE_URL="sqlite+aiosqlite:///:memory:", JWT_SECRET="test-only-secret",
    LTI_CONSUMER_KEY="test", LTI_CONSUMER_SECRET="test", ML_URL="",
)

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assessment_contract.schemas import EvaluationRequest, EvaluationResult
from app.config import settings
from app.database import get_db
from app.main import app
from app.middleware.session import get_current_user
from app.models import AISettings, Attempt, AttemptStatus, FilePurpose, Lab, StoredFile
from app.models.base import Base
from app.schemas.lti import UserContext
from app.services import ml_client, worker
from app.services.ai_snapshot import settings_snapshot


QUALITATIVE = {
    "score": None, "max_score": None, "criteria": [],
    "conclusion": "Числовая шкала не задана. Уточните обработку пустого ввода.",
}
NUMERIC = {
    "score": 8, "max_score": 10, "conclusion": "Есть замечания по обработке данных.",
    "criteria": [{"name": "Корректность", "score": 8, "max_score": 10, "comment": "Проверка граничного случая отсутствует."}],
}
RUBRIC = json.dumps({"criteria": [{"name": "Корректность", "max_score": 10}]})


@pytest_asyncio.fixture
async def database(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(worker, "SessionLocal", sessions)
    monkeypatch.setattr(settings, "ml_retry_delay_seconds", 0)
    monkeypatch.setattr(settings, "ml_max_attempts", 2)
    now = worker.utcnow()
    async with sessions() as db:
        db.add(Lab(id="lab", course_id="course", resource_link_id="resource", title="Исходное задание",
                   created_at=now, updated_at=now))
        db.add(AISettings(lab_id="lab", version=1, methodical_guide_text="Исходная методичка", updated_at=now))
        await db.commit()
    yield sessions
    await engine.dispose()


async def add_attempt(sessions, **changes):
    async with sessions() as db:
        lab = await db.get(Lab, "lab")
        materials = await db.get(AISettings, "lab")
        values = dict(
            id="attempt", lab_id="lab", student_id="student", student_name="Private name",
            number=1, submitted_at=worker.utcnow(), teacher_submitted=False,
            status=AttemptStatus.PROCESSING, settings_version=1,
            ai_input_snapshot=settings_snapshot(lab, materials), ai_processing_attempts=0,
            ai_deadline_at=worker.utcnow() + timedelta(minutes=30),
        )
        values.update(changes)
        db.add(Attempt(**values))
        db.add(StoredFile(id="submission", lab_id="lab", attempt_id="attempt", purpose=FilePurpose.ATTEMPT,
                          filename="Student Private Name.pdf", content_type="application/pdf",
                          size=11, data=b"%PDF-1.4\nxx", created_at=worker.utcnow()))
        await db.commit()


async def get_attempt(sessions):
    async with sessions() as db:
        return await db.get(Attempt, "attempt")


@pytest.mark.asyncio
async def test_completed_result_is_atomic_and_idempotent(database, monkeypatch):
    await add_attempt(database)
    evaluate = AsyncMock(return_value=EvaluationResult.model_validate(QUALITATIVE))
    monkeypatch.setattr(worker, "evaluate", evaluate)
    await worker.process_attempt("attempt")
    await worker.process_attempt("attempt")
    result = await get_attempt(database)
    assert result.status == "ai_checked" and result.ai_score is None
    assert result.ai_checked_at is not None and result.ai_conclusion == QUALITATIVE["conclusion"]
    assert result.ai_processing_attempts == 1 and evaluate.await_count == 1
    payload = evaluate.call_args.args[0]
    assert payload.files[0][1][0] == "submission.pdf"
    assert "Private name" not in payload.metadata.model_dump_json()


@pytest.mark.asyncio
async def test_retry_count_survives_repeated_worker_calls(database, monkeypatch):
    await add_attempt(database)
    evaluate = AsyncMock(side_effect=ml_client.MLFailure("ML_UNAVAILABLE", retryable=True))
    monkeypatch.setattr(worker, "evaluate", evaluate)
    await worker.process_attempt("attempt")
    assert (await get_attempt(database)).status == "processing"
    await worker.process_attempt("attempt")
    await worker.process_attempt("attempt")
    result = await get_attempt(database)
    assert result.status == "ai_failed" and result.ai_error_code == "ML_UNAVAILABLE"
    assert result.ai_processing_attempts == 2 and evaluate.await_count == 2
    assert result.ai_score is None and result.ai_checked_at is None


@pytest.mark.asyncio
async def test_recovery_after_expired_lease_uses_remaining_attempt(database, monkeypatch):
    await add_attempt(database, ai_processing_attempts=1, ai_next_retry_at=worker.utcnow() - timedelta(seconds=1))
    monkeypatch.setattr(worker, "evaluate", AsyncMock(return_value=EvaluationResult.model_validate(QUALITATIVE)))
    await worker.process_attempt("attempt")
    result = await get_attempt(database)
    assert result.status == "ai_checked" and result.ai_processing_attempts == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("change, expected", [
    ({"ai_deadline_at": worker.utcnow() - timedelta(seconds=1)}, "PROCESSING_EXPIRED"),
    ({"ai_input_snapshot": None}, "INVALID_SNAPSHOT"),
    ({"ai_processing_attempts": 2}, "RETRY_LIMIT_EXCEEDED"),
])
async def test_unrecoverable_attempt_never_calls_model(database, monkeypatch, change, expected):
    await add_attempt(database, **change)
    evaluate = AsyncMock()
    monkeypatch.setattr(worker, "evaluate", evaluate)
    await worker.process_attempt("attempt")
    result = await get_attempt(database)
    assert result.status == "ai_failed" and result.ai_error_code == expected
    evaluate.assert_not_called()


@pytest.mark.asyncio
async def test_existing_lease_blocks_duplicate_call(database, monkeypatch):
    await add_attempt(database, ai_processing_attempts=1, ai_next_retry_at=worker.utcnow() + timedelta(seconds=60))
    evaluate = AsyncMock()
    monkeypatch.setattr(worker, "evaluate", evaluate)
    await worker.process_attempt("attempt")
    assert (await get_attempt(database)).ai_processing_attempts == 1
    evaluate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_state", ["accepted", "new_claim"])
async def test_late_result_cannot_overwrite_teacher_or_new_claim(database, monkeypatch, new_state):
    await add_attempt(database)

    async def changed_during_inference(*args):
        async with database() as db:
            attempt = await db.get(Attempt, "attempt")
            if new_state == "accepted":
                attempt.status = "accepted"
            else:
                attempt.ai_processing_attempts += 1
            attempt.ai_conclusion = "Новый результат"
            await db.commit()
        return EvaluationResult.model_validate(QUALITATIVE)

    monkeypatch.setattr(worker, "evaluate", changed_during_inference)
    await worker.process_attempt("attempt")
    result = await get_attempt(database)
    assert result.ai_conclusion == "Новый результат"
    assert result.status == ("accepted" if new_state == "accepted" else "processing")


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong_scope", ["lab", "purpose"])
async def test_material_from_wrong_scope_is_not_transmitted(database, monkeypatch, wrong_scope):
    await add_attempt(database)
    async with database() as db:
        attempt = await db.get(Attempt, "attempt")
        snapshot = dict(attempt.ai_input_snapshot)
        snapshot["materials"] = {"reference_work": {"file_id": "foreign"}}
        attempt.ai_input_snapshot = snapshot
        db.add(StoredFile(id="foreign", lab_id="other" if wrong_scope == "lab" else "lab",
                          purpose=FilePurpose.ATTEMPT if wrong_scope == "purpose" else FilePurpose.AI_SETTING,
                          filename="ref.txt", content_type="text/plain", size=6, data=b"secret", created_at=worker.utcnow()))
        await db.commit()
    evaluate = AsyncMock()
    monkeypatch.setattr(worker, "evaluate", evaluate)
    await worker.process_attempt("attempt")
    assert (await get_attempt(database)).ai_error_code == "MATERIAL_NOT_FOUND"
    evaluate.assert_not_called()


@pytest.mark.asyncio
async def test_upload_snapshot_survives_settings_change_and_public_api_reads_result(database, monkeypatch):
    user = UserContext(sub="student", name="Student", role="student", course_id="course", lab_id="lab")

    async def test_db():
        async with database() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: user
    received = []

    async def evaluate(payload, timeout):
        received.append(payload)
        return EvaluationResult.model_validate(QUALITATIVE)

    monkeypatch.setattr(worker, "evaluate", evaluate)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/labs/lab/attempts", files={"file": ("lab.pdf", b"%PDF-1.4\nxx", "application/pdf")})
            assert response.status_code == 202
            attempt_id = response.json()["id"]
            async with database() as db:
                row = await db.get(AISettings, "lab")
                row.methodical_guide_text = "Новая методичка"
                row.version = 2
                await db.commit()
            await worker.process_attempt(attempt_id)
            result = await client.get(f"/api/attempts/{attempt_id}/ai-result")
            assert result.status_code == 200
            assert result.json()["status"] == "ai_checked"
            assert result.json()["settings_version"] == 1
            assert result.json()["error"] is None
            assert received[0].metadata.materials["methodical_guide"].text == "Исходная методичка"
            sent = await client.post(f"/api/attempts/{attempt_id}/submit-to-teacher")
            assert sent.status_code == 200
            async with database() as db:
                row = await db.get(AISettings, "lab")
                row.methodical_guide_text = None
                await db.commit()
            empty = await client.post("/api/labs/lab/attempts", files={"file": ("lab.pdf", b"%PDF-1.4\nxx", "application/pdf")})
            assert empty.status_code == 409
            assert empty.json()["error"]["code"] == "AI_SETTINGS_NOT_CONFIGURED"
    finally:
        app.dependency_overrides.clear()


def input_payload(rubric=None):
    materials = {"methodical_guide": {"text": "Проверьте решение."}}
    if rubric is not None:
        materials["grading_criteria"] = {"text": rubric}
    return ml_client.EvaluationInput(
        metadata=EvaluationRequest(attempt_id="a", lab_id="l", title="Test", settings_version=1, materials=materials),
        files=[("submission", ("submission.pdf", b"%PDF-x", "application/pdf"))],
    )


def mock_transport(monkeypatch, handler):
    original_client = httpx.AsyncClient
    monkeypatch.setattr(settings, "ml_url", "http://ml.test:8001")
    monkeypatch.setattr(ml_client.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(handler), **kwargs))


@pytest.mark.asyncio
async def test_http_multipart_numeric_result_and_auth_header(monkeypatch):
    def handler(request):
        assert request.url.path == "/evaluate"
        assert request.headers["X-ML-Token"] == "test-token"
        assert b'name="metadata"' in request.content and b'name="submission"' in request.content
        return httpx.Response(200, json=NUMERIC)

    monkeypatch.setattr(settings, "ml_token", "test-token")
    mock_transport(monkeypatch, handler)
    result = await ml_client.evaluate(input_payload(RUBRIC), 5)
    assert result.score == 8


@pytest.mark.asyncio
@pytest.mark.parametrize("response, code", [
    (httpx.Response(200, content=b"not json"), "ML_INVALID_RESPONSE"),
    (httpx.Response(200, json=NUMERIC), "ML_INVALID_RESPONSE"),
    (httpx.Response(200, content=b"x" * (ml_client.MAX_RESPONSE_BYTES + 1)), "ML_INVALID_RESPONSE"),
    (httpx.Response(401, content=b"secret"), "ML_AUTH_FAILED"),
    (httpx.Response(503, json={"error": {"code": "MODEL_UNAVAILABLE", "message": "private traceback", "retryable": True}}), "MODEL_UNAVAILABLE"),
])
async def test_http_rejects_invalid_results_and_sanitizes_errors(monkeypatch, response, code):
    mock_transport(monkeypatch, lambda request: response)
    with pytest.raises(ml_client.MLFailure) as exc:
        await ml_client.evaluate(input_payload(), 5)
    assert exc.value.code == code
    assert "private traceback" not in exc.value.message and "secret" not in exc.value.message


@pytest.mark.asyncio
async def test_network_timeout_is_retryable(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("untrusted remote detail")

    mock_transport(monkeypatch, handler)
    with pytest.raises(ml_client.MLFailure) as exc:
        await ml_client.evaluate(input_payload(), 5)
    assert exc.value.code == "ML_TIMEOUT" and exc.value.retryable
