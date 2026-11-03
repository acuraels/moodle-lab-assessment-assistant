import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Attempt, AttemptStatus

logger = logging.getLogger(__name__)


async def process_attempt(attempt_id: str) -> None:
    """Mark an attempt as failed until an evaluator is implemented."""
    async with SessionLocal() as db:
        attempt = await db.scalar(select(Attempt).where(Attempt.id == attempt_id))
        if attempt is None:
            logger.error("Attempt %s was not found during processing", attempt_id)
            return

        attempt.status = AttemptStatus.AI_FAILED
        await db.commit()
        logger.warning(
            "Attempt %s could not be evaluated: AI evaluation is not implemented",
            attempt_id,
        )
