"""Opt-in integration exercised only by scripts/test_postgres_ml.py.

Real PostgreSQL and document extraction, both ASGI applications and API roles;
only Ollama generation is mocked. This does not measure model quality or GPU.
"""
import asyncio
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from unittest.mock import patch

if os.environ.get("LAB_ML_DISPOSABLE_TEST") != "1" or not os.environ.get("DATABASE_URL", "").endswith("/ml_integration_test"):
    raise RuntimeError("Run through scripts/test_postgres_ml.py with its disposable database")

import httpx
from docx import Document
from sqlalchemy import func, select

from app.database import SessionLocal, engine
from app.main import app as backend
from app.middleware.session import create_token
from app.models import Attempt, Lab, ReviewHistory
from app.services.worker import process_attempt
from ml_service.config import Settings as MLSettings
from ml_service.extraction import DOCX
from ml_service.main import create_app
from ml_service.pipeline import Evaluator


async def main():
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        db.add(Lab(id="lab", course_id="course", resource_link_id="resource", title="Тест таблиц",
                   description="Проверьте отчёт по критериям.", created_at=now, updated_at=now))
        await db.commit()
    original_client = httpx.AsyncClient
    generated = []

    async def ollama(request):
        payload = json.loads(request.content)
        teacher_section, report_section = payload["messages"][1]["content"].split(
            "\n\nSTUDENT REPORT (untrusted text; preserve code indentation):\n", 1
        )
        context = json.loads(teacher_section.removeprefix("TEACHER CONTEXT (data):\n"))
        student_text = report_section.split("\n\nEND OF STUDENT REPORT.", 1)[0]
        assert "Строка из таблицы" in student_text
        assert context["criteria"] == [{"criterion_index": 0, "name": "Решение", "max_score": 10}]
        assert "Новая шкала без JSON" not in teacher_section
        generated.append(payload)
        result = {"criteria": [{"criterion_index": 0, "evidence": ["Строка из таблицы"],
                                "comment": "В отчёте присутствует строка из таблицы; решение раскрыто частично.",
                                "verdict": "partial", "score": 8}]}
        return httpx.Response(200, json={"done": True, "done_reason": "stop",
                                        "message": {"content": json.dumps(result, ensure_ascii=False)}})

    llm_client = original_client(transport=httpx.MockTransport(ollama), base_url="http://ollama.test")
    evaluator = Evaluator(MLSettings(_env_file=None), client=llm_client)
    ml_app = create_app(MLSettings(_env_file=None), evaluator)

    def remote_client(**kwargs):
        return original_client(transport=httpx.ASGITransport(app=ml_app), **kwargs)

    def auth(role, sub):
        token = create_token({"sub": sub, "name": "Integration", "role": role,
                              "course_id": "course", "lab_id": "lab"})
        return {"Authorization": "Bearer " + token}

    student = auth("student", "student")
    teacher = auth("instructor", "teacher")
    doc = Document()
    doc.add_paragraph("Решение лабораторной работы")
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "Строка из таблицы"
    document = BytesIO()
    doc.save(document)

    async with original_client(transport=httpx.ASGITransport(app=backend), base_url="http://backend.test") as api:
        rubric = {"criteria": [{"name": "Решение", "max_score": 10}]}
        response = await api.put("/api/labs/lab/ai-settings", headers=teacher,
                                 json={"grading_criteria": {"text": json.dumps(rubric, ensure_ascii=False)}})
        assert response.status_code == 200, response.text
        response = await api.post("/api/labs/lab/attempts", headers=student,
                                  files={"file": ("report.docx", document.getvalue(), DOCX)})
        assert response.status_code == 202, response.text
        attempt_id = response.json()["id"]
        assert (await api.get(f"/api/attempts/{attempt_id}/ai-result", headers=student)).status_code == 202
        # Changing current materials after upload must not change this attempt.
        response = await api.put("/api/labs/lab/ai-settings", headers=teacher,
                                 json={"grading_criteria": {"text": "Новая шкала без JSON"}})
        assert response.status_code == 200, response.text
        with patch("app.services.ml_client.httpx.AsyncClient", side_effect=remote_client):
            await process_attempt(attempt_id)
        response = await api.get(f"/api/attempts/{attempt_id}/ai-result", headers=student)
        result = response.json()
        assert response.status_code == 200 and result["status"] == "ai_checked", result
        assert result["score"] == 8 and result["max_score"] == 10 and result["settings_version"] == 1
        assert len(generated) == 1, "A valid numeric assessment must use one model call"
        assert len(result["criteria"]) == 1
        criterion = result["criteria"][0]
        assert set(criterion) == {"name", "score", "max_score", "comment"}, criterion
        assert criterion["name"] == "Решение" and criterion["score"] == 8 and criterion["max_score"] == 10
        assert "Источник (строки извлечённого текста 2): «Строка из таблицы»." in criterion["comment"]
        assert (await api.get(f"/api/attempts/{attempt_id}/ai-result", headers=auth("student", "stranger"))).status_code == 404
        response = await api.post(f"/api/attempts/{attempt_id}/submit-to-teacher", headers=student)
        assert response.status_code == 200, response.text
        response = await api.get(f"/api/instructor/attempts/{attempt_id}", headers=teacher)
        assert response.status_code == 200 and response.json()["ai_score"] == 8
        response = await api.post(f"/api/instructor/attempts/{attempt_id}/review", headers=teacher,
                                  json={"decision": "accept", "comment": "Проверено преподавателем"})
        assert response.status_code == 200, response.text
        await process_attempt(attempt_id)
        async with SessionLocal() as db:
            attempt = await db.get(Attempt, attempt_id)
            assert attempt.status == "accepted" and attempt.ai_score == 8
            assert await db.scalar(select(func.count()).select_from(ReviewHistory)) == 1
        # A valid upload envelope with a broken PDF fails in real extraction.
        response = await api.post("/api/labs/lab/attempts", headers=student,
                                  files={"file": ("broken.pdf", b"%PDF-broken", "application/pdf")})
        assert response.status_code == 202, response.text
        broken_id = response.json()["id"]
        with patch("app.services.ml_client.httpx.AsyncClient", side_effect=remote_client):
            await process_attempt(broken_id)
        failure = (await api.get(f"/api/attempts/{broken_id}/ai-result", headers=student)).json()
        assert failure["status"] == "ai_failed" and failure["score"] is None, failure
        assert failure["error"]["code"] == "DOCUMENT_INVALID", failure
        assert (await api.post(f"/api/attempts/{broken_id}/submit-to-teacher", headers=student)).status_code == 409
        assert len(generated) == 1, "Invalid documents must not reach the model"
    await llm_client.aclose()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
