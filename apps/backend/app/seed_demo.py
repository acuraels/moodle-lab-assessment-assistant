import asyncio
from datetime import datetime, timedelta, timezone
from os import getenv

from sqlalchemy import delete, select
from uuid import NAMESPACE_URL, uuid5

from app.database import SessionLocal
from app.middleware.session import create_token
from app.models import (
    AISettings,
    Attempt,
    AttemptStatus,
    FilePurpose,
    Lab,
    ReviewHistory,
    StoredFile,
)

COURSE_ID = getenv("DEMO_COURSE_ID", "2") ## http://localhost/course/view.php?id=1
RESOURCE_LINK_ID = getenv("DEMO_RESOURCE_LINK_ID", "2") ## найти resource_link_id в /lti/launch при запуске лабы
INSTRUCTOR_ID = getenv("DEMO_INSTRUCTOR_ID", "3") ## http://localhost/user/profile.php?id=1
STUDENT_1_ID = getenv("DEMO_STUDENT_1_ID", "4") ## http://localhost/user/profile.php?id=2


async def seed() -> None:
    now = datetime.now(timezone.utc)
    demo_attempt_ids = {
        "demo-attempt-processing",
        "demo-attempt-ai-checked",
        "demo-attempt-accepted",
        "demo-attempt-revision",
        "demo-attempt-failed",
    }

    async with SessionLocal() as db:
        lab = await db.scalar(
            select(Lab).where(
                Lab.course_id == COURSE_ID,
                Lab.resource_link_id == RESOURCE_LINK_ID,
            )
        )
        if lab is None:
            lab = Lab(
                id=str(uuid5(NAMESPACE_URL, f"{COURSE_ID}:{RESOURCE_LINK_ID}")),
                course_id=COURSE_ID,
                resource_link_id=RESOURCE_LINK_ID,
                title="Демонстрационная лабораторная №1",
                description="Тестовые данные для проверки интерфейса преподавателя и студента.",
                deadline=now + timedelta(days=14),
                attempts_limit=None,
                created_at=now,
                updated_at=now,
            )
            db.add(lab)
        else:
            lab.title = "Демонстрационная лабораторная №1"
            lab.description = "Тестовые данные для проверки интерфейса преподавателя и студента."
            lab.updated_at = now

        lab_id = lab.id
        settings = await db.get(AISettings, lab_id)
        if settings is None:
            settings = AISettings(lab_id=lab_id, version=1, updated_at=now)
            db.add(settings)
        settings.methodical_guide_text = "Методические указания для демонстрационной лабораторной."
        settings.grading_criteria_text = "Корректность решения — 5 баллов; оформление — 5 баллов."
        settings.system_instructions_text = "Оцени работу по указанным критериям и дай краткое заключение."
        settings.reference_work_text = "Эталонная работа для демонстрации."
        settings.updated_at = now

        await db.execute(
            delete(ReviewHistory).where(
                ReviewHistory.attempt_id.in_(demo_attempt_ids)
            )
        )
        await db.execute(delete(StoredFile).where(StoredFile.attempt_id.in_(demo_attempt_ids)))
        await db.execute(delete(Attempt).where(Attempt.id.in_(demo_attempt_ids)))

        attempts = [
            _attempt(
                lab_id,
                "demo-attempt-processing",
                STUDENT_1_ID,
                "Иванов Иван Иванович",
                "ИВТ-301",
                1,
                AttemptStatus.PROCESSING,
                now - timedelta(hours=1),
            ),
            _attempt(
                lab_id,
                "demo-attempt-ai-checked",
                STUDENT_1_ID,
                "Иванов Иван Иванович",
                "ИВТ-301",
                2,
                AttemptStatus.AI_CHECKED,
                now - timedelta(days=1),
                score=8.5,
                submitted_to_teacher=True,
                conclusion="Работа соответствует большинству критериев.",
            ),
            _attempt(
                lab_id,
                "demo-attempt-accepted",
                STUDENT_1_ID,
                "Иванов Иван Иванович",
                "ИВТ-301",
                1,
                AttemptStatus.ACCEPTED,
                now - timedelta(days=2),
                score=9.5,
                submitted_to_teacher=True,
                conclusion="Работа выполнена корректно.",
                teacher_comment="Работа принята.",
                reviewed=True,
            ),
            _attempt(
                lab_id,
                "demo-attempt-revision",
                STUDENT_1_ID,
                "Иванов Иван Иванович",
                "ИВТ-301",
                2,
                AttemptStatus.RETURNED_FOR_REVISION,
                now - timedelta(days=3),
                score=5.0,
                submitted_to_teacher=True,
                conclusion="Есть существенные недочёты в оформлении.",
                teacher_comment="Исправьте раздел 2 и приложите результаты эксперимента.",
                reviewed=True,
            ),
            _attempt(
                lab_id,
                "demo-attempt-failed",
                STUDENT_1_ID,
                "Иванов Иван Иванович",
                "ИВТ-301",
                3,
                AttemptStatus.AI_FAILED,
                now - timedelta(days=4),
            ),
        ]
        db.add_all(attempts)

        for attempt in attempts:
            db.add(
                StoredFile(
                    id=f"{attempt.id}-file",
                    lab_id=lab_id,
                    attempt_id=attempt.id,
                    purpose=FilePurpose.ATTEMPT,
                    filename=f"{attempt.student_id}-lab.pdf",
                    content_type="application/pdf",
                    size=len(b"%PDF-demo"),
                    data=b"%PDF-demo",
                    created_at=attempt.submitted_at,
                )
            )
            if attempt.reviewed_at is not None:
                db.add(
                    ReviewHistory(
                        id=f"{attempt.id}-review",
                        attempt_id=attempt.id,
                        decision=(
                            "accept"
                            if attempt.status == AttemptStatus.ACCEPTED
                            else "return_for_revision"
                        ),
                        comment=attempt.teacher_comment,
                        reviewed_by=INSTRUCTOR_ID,
                        reviewed_at=attempt.reviewed_at,
                        ai_score=attempt.ai_score,
                        ai_max_score=attempt.ai_max_score,
                    )
                )

        await db.commit()

    print("Demo data seeded.")
    print("Instructor token:")
    print(_token(lab_id, INSTRUCTOR_ID, "Test Instructor", "instructor@example.com", "instructor"))
    print("Student token:")
    print(_token(lab_id, STUDENT_1_ID, "Иванов Иван Иванович", "student1@example.com", "student"))


def _attempt(
    lab_id: str,
    attempt_id: str,
    student_id: str,
    student_name: str,
    group: str,
    number: int,
    status: AttemptStatus,
    submitted_at: datetime,
    *,
    score: float | None = None,
    submitted_to_teacher: bool = False,
    conclusion: str | None = None,
    teacher_comment: str | None = None,
    reviewed: bool = False,
) -> Attempt:
    reviewed_at = submitted_at + timedelta(hours=2) if reviewed else None
    return Attempt(
        id=attempt_id,
        lab_id=lab_id,
        student_id=student_id,
        student_name=student_name,
        academic_group=group,
        number=number,
        submitted_at=submitted_at,
        teacher_submitted=submitted_to_teacher,
        teacher_submitted_at=submitted_at + timedelta(minutes=5)
        if submitted_to_teacher
        else None,
        status=status,
        ai_score=score,
        ai_max_score=10.0 if score is not None else None,
        ai_conclusion=conclusion,
        ai_criteria=[
            {
                "name": "Корректность решения",
                "score": score / 2 if score is not None else 0,
                "max_score": 5,
                "comment": "Демонстрационный результат.",
            }
        ]
        if score is not None
        else None,
        settings_version=1,
        ai_checked_at=submitted_at + timedelta(minutes=1)
        if score is not None
        else None,
        teacher_comment=teacher_comment,
        reviewed_by=INSTRUCTOR_ID if reviewed else None,
        reviewed_at=reviewed_at,
    )


def _token(lab_id: str, user_id: str, name: str, email: str, role: str) -> str:
    return create_token(
        {
            "sub": user_id,
            "email": email,
            "name": name,
            "role": role,
            "course_id": COURSE_ID,
            "lab_id": lab_id,
            "lab_title": "Демонстрационная лабораторная №1",
            "Academic_group": "ИВТ-301" if role == "student" else None,
        }
    )


if __name__ == "__main__":
    asyncio.run(seed())
