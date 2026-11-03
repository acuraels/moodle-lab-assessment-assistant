"""Add teacher submission time and review history."""

from alembic import op
import sqlalchemy as sa


revision = "0002_review_history"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attempts",
        sa.Column("teacher_submitted_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        "UPDATE attempts SET teacher_submitted_at = submitted_at "
        "WHERE teacher_submitted = true"
    )
    op.create_index(
        "ix_attempts_teacher_submitted_at",
        "attempts",
        ["teacher_submitted_at"],
    )
    op.create_table(
        "review_history",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.String(128),
            sa.ForeignKey("attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("reviewed_by", sa.String(255), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_score", sa.Float()),
        sa.Column("ai_max_score", sa.Float()),
    )
    op.create_index("ix_review_history_attempt_id", "review_history", ["attempt_id"])
    op.create_index("ix_review_history_reviewed_at", "review_history", ["reviewed_at"])


def downgrade() -> None:
    op.drop_table("review_history")
    op.drop_index("ix_attempts_teacher_submitted_at", table_name="attempts")
    op.drop_column("attempts", "teacher_submitted_at")
