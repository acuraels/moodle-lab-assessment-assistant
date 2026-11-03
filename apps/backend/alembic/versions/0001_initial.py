"""Create lab assessment tables.

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labs",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("course_id", sa.String(255), nullable=False),
        sa.Column("resource_link_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("attempts_limit", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("course_id", "resource_link_id"),
    )
    op.create_index("ix_labs_course_id", "labs", ["course_id"])
    op.create_index("ix_labs_resource_link_id", "labs", ["resource_link_id"])
    op.create_table(
        "ai_settings",
        sa.Column("lab_id", sa.String(128), sa.ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("methodical_guide_text", sa.Text()),
        sa.Column("methodical_guide_file_id", sa.String(128)),
        sa.Column("grading_criteria_text", sa.Text()),
        sa.Column("grading_criteria_file_id", sa.String(128)),
        sa.Column("system_instructions_text", sa.Text()),
        sa.Column("system_instructions_file_id", sa.String(128)),
        sa.Column("reference_work_text", sa.Text()),
        sa.Column("reference_work_file_id", sa.String(128)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("lab_id", sa.String(128), sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.String(255), nullable=False),
        sa.Column("student_name", sa.String(255), nullable=False),
        sa.Column("Academic_group", sa.String(255)),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("teacher_submitted", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("ai_score", sa.Float()),
        sa.Column("ai_max_score", sa.Float()),
        sa.Column("ai_conclusion", sa.Text()),
        sa.Column("ai_criteria", sa.JSON()),
        sa.Column("settings_version", sa.Integer()),
        sa.Column("ai_checked_at", sa.DateTime(timezone=True)),
        sa.Column("teacher_comment", sa.Text()),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    for column in ("lab_id", "student_id", "submitted_at", "teacher_submitted", "status"):
        op.create_index(f"ix_attempts_{column}", "attempts", [column])
    op.create_table(
        "stored_files",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("lab_id", sa.String(128), sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_id", sa.String(128), sa.ForeignKey("attempts.id", ondelete="CASCADE")),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("field", sa.String(64)),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stored_files_lab_id", "stored_files", ["lab_id"])
    op.create_index("ix_stored_files_attempt_id", "stored_files", ["attempt_id"])


def downgrade() -> None:
    op.drop_table("stored_files")
    op.drop_table("attempts")
    op.drop_table("ai_settings")
    op.drop_table("labs")
