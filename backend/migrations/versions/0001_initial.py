from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "students",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("teacher_id", sa.String(), nullable=False),
        sa.Column("class_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_students_teacher_id", "students", ["teacher_id"])
    op.create_index("ix_students_class_id", "students", ["class_id"])

    op.create_table(
        "work_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("teacher_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("tasks", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_work_templates_teacher_id", "work_templates", ["teacher_id"]
    )

    op.create_table(
        "student_profiles",
        sa.Column(
            "student_id",
            sa.String(),
            sa.ForeignKey("students.id"),
            primary_key=True,
        ),
        sa.Column("submissions_count", sa.Integer(), nullable=False),
        sa.Column("avg_score", sa.Float(), nullable=False),
        sa.Column("memory", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "work_id",
            sa.String(),
            sa.ForeignKey("work_templates.id"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.String(),
            sa.ForeignKey("students.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("photos", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_submissions_work_id", "submissions", ["work_id"])
    op.create_index("ix_submissions_student_id", "submissions", ["student_id"])
    op.create_index("ix_submissions_status", "submissions", ["status"])

    op.create_table(
        "check_results",
        sa.Column(
            "submission_id",
            sa.String(),
            sa.ForeignKey("submissions.id"),
            primary_key=True,
        ),
        sa.Column("per_task", JSONB(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("check_results")
    op.drop_table("submissions")
    op.drop_table("student_profiles")
    op.drop_table("work_templates")
    op.drop_table("students")