"""Persist immutable ML input and bounded processing state."""

from alembic import op
import sqlalchemy as sa


revision = "0003_ml_processing"
down_revision = "0002_review_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attempts", sa.Column("ai_input_snapshot", sa.JSON()))
    op.add_column("attempts", sa.Column("ai_error_code", sa.String(64)))
    op.add_column("attempts", sa.Column("ai_error_message", sa.Text()))
    op.add_column("attempts", sa.Column("ai_processing_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("attempts", sa.Column("ai_next_retry_at", sa.DateTime(timezone=True)))
    op.add_column("attempts", sa.Column("ai_deadline_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    for name in (
        "ai_deadline_at", "ai_next_retry_at", "ai_processing_attempts",
        "ai_error_message", "ai_error_code", "ai_input_snapshot",
    ):
        op.drop_column("attempts", name)
