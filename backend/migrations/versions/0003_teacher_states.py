"""Add teacher_states table for shared bot/miniapp context."""

from alembic import op
import sqlalchemy as sa


revision = "0003_teacher_states"
down_revision = "0002_anonymize_students"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "teacher_states",
        sa.Column("teacher_id", sa.String(), primary_key=True),
        sa.Column(
            "current_work_id",
            sa.String(),
            sa.ForeignKey("work_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "current_student_id",
            sa.String(),
            sa.ForeignKey("students.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("teacher_states")
